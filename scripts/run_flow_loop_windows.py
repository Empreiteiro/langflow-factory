import requests
import time
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import msvcrt

def log_with_timestamp(message):
    """Add timestamp to log messages"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_for_keypress():
    """Check for keypress on Windows (non-blocking)"""
    if msvcrt.kbhit():
        key = msvcrt.getch().decode('utf-8').lower()
        return key
    return None

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Run a Langflow flow in a loop with configurable intervals (Windows version)')
    parser.add_argument('--flow-id', type=str, 
                       default=os.getenv('LANGFLOW_FLOW_ID'),
                       help='Flow ID to run (can be set via LANGFLOW_FLOW_ID env var)')
    parser.add_argument('--input-value', type=str, 
                       default=os.getenv('LANGFLOW_INPUT_VALUE', 'hello world!'),
                       help='Input value for the flow (default: "hello world!")')
    parser.add_argument('--output-type', type=str, 
                       default=os.getenv('LANGFLOW_OUTPUT_TYPE', 'chat'),
                       choices=['chat', 'text', 'json'],
                       help='Output type (default: chat)')
    parser.add_argument('--input-type', type=str, 
                       default=os.getenv('LANGFLOW_INPUT_TYPE', 'text'),
                       choices=['text', 'json'],
                       help='Input type (default: text)')
    parser.add_argument('--interval', type=int, 
                       default=int(os.getenv('LANGFLOW_INTERVAL', '5')),
                       help='Interval in seconds between requests (default: 5)')
    parser.add_argument('--max-requests', type=int, 
                       default=int(os.getenv('LANGFLOW_MAX_REQUESTS', '0')),
                       help='Maximum number of requests (0 = unlimited, default: 0)')
    
    args = parser.parse_args()
    
    # Get API configuration from environment
    api_key = os.getenv('LANGFLOW_TOKEN')
    base_url = os.getenv('LANGFLOW_URL', 'http://localhost:3000')
    
    if not api_key:
        log_with_timestamp("ERROR: LANGFLOW_TOKEN environment variable is required")
        return 1
    
    if not args.flow_id:
        log_with_timestamp("ERROR: Flow ID is required. Use --flow-id parameter or set LANGFLOW_FLOW_ID environment variable")
        return 1
    
    # Build URL
    url = f"{base_url.rstrip('/')}/api/v1/run/{args.flow_id}"
    
    # Payload
    payload = {
        "output_type": args.output_type,
        "input_type": args.input_type,
        "input_value": args.input_value
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    log_with_timestamp(f"🎯 Starting flow loop for Flow ID: {args.flow_id}")
    log_with_timestamp(f"🌐 Langflow URL: {base_url}")
    log_with_timestamp(f"📝 Input value: {args.input_value}")
    log_with_timestamp(f"⏱️  Interval: {args.interval} seconds")
    log_with_timestamp(f"🔢 Max requests: {'unlimited' if args.max_requests == 0 else args.max_requests}")
    log_with_timestamp("⌨️  Press 'q' to stop the loop or Ctrl+C to force exit\n")
    
    request_count = 0
    
    try:
        while True:
            # Check if we've reached the maximum number of requests
            if args.max_requests > 0 and request_count >= args.max_requests:
                log_with_timestamp(f"Reached maximum number of requests ({args.max_requests}). Stopping.")
                break
            
            # Check for 'q' keypress during the interval
            log_with_timestamp(f"Waiting {args.interval} seconds before next request... (press 'q' to stop)")
            
            for i in range(args.interval * 10):  # Check every 0.1 seconds
                key = check_for_keypress()
                if key == 'q':
                    log_with_timestamp("User pressed 'q'. Ending program...")
                    return 0
                time.sleep(0.1)
            
            try:
                log_with_timestamp(f"Sending request #{request_count + 1}...")
                
                # Send POST request
                response = requests.request("POST", url, json=payload, headers=headers, timeout=30)
                
                log_with_timestamp(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    log_with_timestamp("✅ Request successful")
                    log_with_timestamp("📄 Response:")
                    
                    # Try to pretty print JSON response if possible
                    try:
                        response_json = response.json()
                        print(json.dumps(response_json, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(response.text)
                        
                elif response.status_code == 401:
                    log_with_timestamp("❌ ERROR: Authentication failed. Check your API key.")
                    break
                elif response.status_code == 404:
                    log_with_timestamp("❌ ERROR: Flow not found. Check your Flow ID.")
                    break
                else:
                    log_with_timestamp(f"⚠️  WARNING: Unexpected status code {response.status_code}")
                    print(response.text)
                
                request_count += 1
                
            except requests.exceptions.Timeout:
                log_with_timestamp("ERROR: Request timeout (30s)")
            except requests.exceptions.ConnectionError:
                log_with_timestamp("ERROR: Connection failed. Check if Langflow is running.")
            except requests.exceptions.RequestException as e:
                log_with_timestamp(f"ERROR: Request failed: {e}")
            except Exception as e:
                log_with_timestamp(f"ERROR: Unexpected error: {e}")
        
    except KeyboardInterrupt:
        log_with_timestamp("Program interrupted by user (Ctrl+C)")
    
    log_with_timestamp(f"Program ended. Total requests sent: {request_count}")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 