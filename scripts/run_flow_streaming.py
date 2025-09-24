import requests
import os
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv 
import time 

"""
Run Flow Script for Langflow with Streaming Support
==================================================

This script runs a specified flow in Langflow with optional token streaming.
It allows you to execute flows with custom parameters and tweaks, and stream
LLM token responses in real-time.

USAGE:
------
Basic usage:
    python run_flow_streaming.py

With streaming enabled:
    python run_flow_streaming.py --stream

With custom parameters:
    python run_flow_streaming.py --flow-id YOUR_FLOW_ID --input-value "Process this text"

With custom Langflow server:
    python run_flow_streaming.py --langflow-url http://your-server:3000 --langflow-token your_token

ENVIRONMENT VARIABLES:
---------------------
Create a .env file with the following variables:
    LANGFLOW_URL=http://localhost:3000
    LANGFLOW_TOKEN=your_api_token_here
    FLOW_ID=your_default_flow_id

COMMAND LINE ARGUMENTS:
----------------------
    --langflow-url      Langflow server URL (default: LANGFLOW_URL env var or http://localhost:3000)
    --langflow-token    Langflow API token (default: LANGFLOW_TOKEN env var)
    --flow-id           Flow ID to run (default: FLOW_ID env var)
    --input-value       Message for the flow (default: "hello world!")
    --tweaks            Custom tweaks as JSON string (optional)
    --stream            Enable token streaming (default: False)
    --session-id        Session ID for conversation context (optional)

CUSTOMIZING TWEAKS FOR YOUR FLOW:
---------------------------------
You can customize the flow execution by providing tweaks. Tweaks allow you to override
component parameters at runtime.

Examples:

1. Simple text input override:
   python run_flow.py --tweaks '{"TextInput-xyz123": {"input_value": "Custom text"}}'

2. Multiple component tweaks:
   python run_flow.py --tweaks '{
       "TextInput-abc123": {"input_value": "Hello"},
       "NumberInput-def456": {"input_value": 42},
       "DropDown-ghi789": {"input_value": "option1"}
   }'

3. Custom component parameters:
   python run_flow.py --tweaks '{
       "CustomComponent-abc456": {
           "parameter1": "value1",
           "parameter2": "value2",
           "user_id": "user123"
       }
   }'

FINDING COMPONENT IDS:
---------------------
To find component IDs for tweaks:
1. Open your flow in Langflow
2. Check component IDs in the flow editor
3. Component IDs typically look like "ComponentName-ABC12"
4. Or export your flow as JSON and look at the "data" section

EXAMPLES:
--------
# Run flow with default settings
python run_flow_streaming.py

# Run with streaming enabled
python run_flow_streaming.py --stream

# Run with custom message and streaming
python run_flow_streaming.py --input-value "Tell me a story" --stream

# Use a different flow with streaming
python run_flow_streaming.py --flow-id "abc123-def456-ghi789" --stream

# Run with custom tweaks and streaming
python run_flow_streaming.py --input-value "Hello" --tweaks '{"TextInput-xyz": {"input_value": "Custom input"}}' --stream

# Connect to remote Langflow instance with streaming
python run_flow_streaming.py --langflow-url https://my-langflow.com --langflow-token sk_token_here --stream

# Use session ID for conversation context
python run_flow_streaming.py --session-id "chat-123" --stream

# Enable debug mode to see raw streaming data
python run_flow_streaming.py --stream --debug

ERROR HANDLING:
--------------
The script provides detailed error messages for common issues:
- Invalid API tokens
- Network connectivity problems
- Flow execution errors
- Invalid JSON in tweaks

Check the console output for specific error details and suggestions.
"""

def log(message, end="\n"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", end=end)

def stream_flow(api_key, langflow_url, flow_id, input_value="hello world!", tweaks=None, output_type="chat", input_type="chat", session_id=None, debug=False):
    """
    Run the Langflow flow with streaming enabled.
    
    Args:
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
        flow_id (str): The flow ID to run
        input_value (str): Input value for the flow
        tweaks (dict): Custom tweaks for components
        output_type (str): Output type (default: "chat")
        input_type (str): Input type (default: "chat")
        session_id (str): Session ID for conversation context
        debug (bool): Enable debug mode to see raw streaming data
    """
    
    # Ensure URL doesn't have double slashes
    langflow_url = langflow_url.rstrip('/')
    flow_url = f"{langflow_url}/api/v1/run/{flow_id}?stream=true"
    
    # Simplified payload as per Langflow documentation example
    payload = {
        "message": input_value
    }
    
    # Add session_id if provided
    if session_id:
        payload["session_id"] = session_id
    
    # Add tweaks if provided
    if tweaks:
        payload["tweaks"] = tweaks
        log(f"📝 Using custom tweaks: {json.dumps(tweaks, indent=2)}")
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    try:
        log("🚀 Starting streaming flow...")
        log(f"🎯 Flow ID: {flow_id}")
        log(f"📝 Message: {input_value}")
        if session_id:
            log(f"🔗 Session ID: {session_id}")
        
        log("🌊 Streaming response:")
        log("=" * 50)
        
        # Make streaming request
        response = requests.post(flow_url, json=payload, headers=headers, stream=True)
        response.raise_for_status()
        
        # Process streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    # Decode the line
                    line_str = line.decode('utf-8')
                    
                    # Debug: Print raw line for analysis
                    if debug:
                        log(f"🔍 Raw line: {line_str}")
                    
                    # Parse JSON event
                    event_data = json.loads(line_str)
                    event_type = event_data.get("event")
                    data = event_data.get("data", {})
                    
                    if debug:
                        log(f"📋 Event: {event_type}")
                    
                    if event_type == "token":
                        # Stream token - according to Langflow docs
                        chunk = data.get("chunk", "")
                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk
                    
                    elif event_type == "add_message":
                        # Message added event
                        sender = data.get("sender", "")
                        text = data.get("text", "")
                        if sender == "User":
                            log(f"👤 User: {text}")
                        elif sender == "Machine":
                            if text:
                                log(f"🤖 AI: {text}")
                    
                    elif event_type == "end":
                        # End of streaming - according to Langflow docs
                        log("\n" + "=" * 50)
                        log("✅ Streaming completed!")
                        
                        # Extract final result if available
                        result = data.get("result", {})
                        if result:
                            log("📄 Final Result:")
                            log(json.dumps(result, indent=2, ensure_ascii=False))
                        
                        return result
                    
                    else:
                        # Handle other event types
                        if debug:
                            log(f"📝 Other event: {event_type}")
                            log(f"📝 Data: {json.dumps(data, indent=2)}")
                    
                except json.JSONDecodeError as e:
                    # Skip invalid JSON lines but log them
                    log(f"⚠️  Invalid JSON line: {line_str}")
                    log(f"⚠️  Error: {e}")
                    continue
                except Exception as e:
                    log(f"⚠️  Error processing stream line: {e}")
                    log(f"⚠️  Line: {line_str}")
                    continue
        
        log("\n" + "=" * 50)
        log("✅ Streaming completed!")
        return {"message": full_response}
        
    except requests.exceptions.RequestException as e:
        log(f"❌ Error making streaming API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Response status: {e.response.status_code}")
            log(f"Response text: {e.response.text}")
        raise

def run_flow(api_key, langflow_url, flow_id, input_value="hello world!", tweaks=None, output_type="chat", input_type="chat", session_id=None):
    """
    Run the Langflow flow with specified parameters.
    
    Args:
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
        flow_id (str): The flow ID to run
        input_value (str): Input value for the flow
        tweaks (dict): Custom tweaks for components
        output_type (str): Output type (default: "chat")
        input_type (str): Input type (default: "chat")
        session_id (str): Session ID for conversation context
    """
    
     # Ensure URL doesn't have double slashes
    langflow_url = langflow_url.rstrip('/')
    flow_url = f"{langflow_url}/api/v1/run/{flow_id}"
    
    # Simplified payload as per Langflow documentation example
    payload = {
        "message": input_value
    }
    
    # Add session_id if provided
    if session_id:
        payload["session_id"] = session_id
    
    # Add tweaks if provided
    if tweaks:
        payload["tweaks"] = tweaks
        log(f"📝 Using custom tweaks: {json.dumps(tweaks, indent=2)}")
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    try:
        log("🚀 Running flow...")
        log(f"🎯 Flow ID: {flow_id}")
        log(f"📝 Input: {input_value}")
        log(f"📤 Input Type: {input_type}")
        log(f"📥 Output Type: {output_type}")
        
        response = requests.request(
            "POST", flow_url, json=payload, headers=headers
        )
        
        log(f"📊 Status Code: {response.status_code}")
        
        response.raise_for_status()
        
        log("✅ Flow executed successfully!")
        log("📄 Response:")
        
        # Try to pretty print JSON response if possible
        try:
            response_json = response.json()
            log(json.dumps(response_json, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            log(response.text)
        
        return response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
    except requests.exceptions.RequestException as e:
        log(f"❌ Error making API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Response status: {e.response.status_code}")
            log(f"Response text: {e.response.text}")
        raise

def main():
    """Main function to run the flow."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run Langflow flow")
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_URL", "http://localhost:3000"),
        help="Langflow URL (default: from LANGFLOW_URL env var or http://localhost:3000)"
    )
    parser.add_argument(
        "--langflow-token",
        default=os.getenv("LANGFLOW_TOKEN"),
        help="Langflow API token (default: from LANGFLOW_TOKEN env var)"
    )
    parser.add_argument(
        "--flow-id",
        default=os.getenv("FLOW_ID"),
        help="Flow ID to run (default: from FLOW_ID env var)"
    )
    parser.add_argument(
        "--input-value",
        default="hello world!",
        help="Input value for the flow (default: 'hello world!')"
    )
    parser.add_argument(
        "--tweaks",
        help="Custom tweaks as JSON string (optional)"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable token streaming (default: False)"
    )
    parser.add_argument(
        "--session-id",
        help="Session ID for conversation context (optional)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode to see raw streaming data"
    )
    
    args = parser.parse_args()
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API key in the .env file or use --langflow-token parameter")
        sys.exit(1)
    
    # Check if flow ID is available
    if not args.flow_id:
        log("❌ Error: FLOW_ID not specified.")
        log("Please set FLOW_ID in the .env file or use --flow-id parameter")
        sys.exit(1)
    
    # Parse tweaks if provided
    tweaks = None
    if args.tweaks:
        try:
            tweaks = json.loads(args.tweaks)
        except json.JSONDecodeError as e:
            log(f"❌ Error parsing tweaks JSON: {e}")
            log("Please ensure tweaks are in valid JSON format")
            sys.exit(1)
    
    try:
        log("🎯 Starting flow execution...")
        
        if args.stream:
            # Use streaming flow
            result = stream_flow(
                args.langflow_token, 
                args.langflow_url, 
                args.flow_id, 
                args.input_value,
                tweaks,
                session_id=args.session_id,
                debug=args.debug
            )
        else:
            # Use regular flow
            result = run_flow(
                args.langflow_token, 
                args.langflow_url, 
                args.flow_id, 
                args.input_value,
                tweaks,
                session_id=args.session_id
            )
        
        log("🎉 Flow execution completed!")
        
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 