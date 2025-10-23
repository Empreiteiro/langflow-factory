import requests
import os
import sys
import argparse
import json
import time
import threading
import uuid
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

"""
Batch Flow Runner Script for Langflow Cloud
============================================

This script runs multiple requests to the same Langflow Cloud flow simultaneously.
Perfect for load testing, batch processing, or stress testing your flows.

USAGE:
------
Basic usage (10 requests):
    python run_flow_cloud_batch.py --count 10

Custom requests with different inputs:
    python run_flow_cloud_batch.py --count 5 --input-value "Test batch processing"

High concurrency testing:
    python run_flow_cloud_batch.py --count 100 --workers 20

With custom tweaks for all requests:
    python run_flow_cloud_batch.py --count 50 --tweaks '{"TextInput-xyz": {"input_value": "Batch test"}}'

ENVIRONMENT VARIABLES:
---------------------
Create a .env file with the following variables:
    LANGFLOW_URL=https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID/api/v1/run/YOUR_FLOW_ID
    LANGFLOW_TOKEN=your_application_token_here
    LANGFLOW_CURRENT_ORG=your_org_id_here

COMMAND LINE ARGUMENTS:
----------------------
    --count             Number of requests to send (required)
    --workers           Number of concurrent workers (default: 10)
    --langflow-url      Complete Langflow Cloud API endpoint URL (default: LANGFLOW_URL env var)
    --langflow-token    Langflow Application Token (default: LANGFLOW_TOKEN env var)
    --langflow-org      Langflow Organization ID (default: LANGFLOW_CURRENT_ORG env var)
    --flow-id           Flow ID (optional, builds URL if base URL is provided)
    --input-value       Input value for all requests (default: "batch test")
    --tweaks            Custom tweaks as JSON string (optional)
    --output-type       Output type (default: "chat")
    --input-type        Input type (default: "text")
    --delay             Delay between request batches in seconds (default: 0)
    --timeout           Request timeout in seconds (default: 30)

EXAMPLES:
--------
# Send 20 requests with 5 concurrent workers
python run_flow_cloud_batch.py --count 20 --workers 5

# Load test with 100 requests
python run_flow_cloud_batch.py --count 100 --workers 20 --input-value "Load test"

# Batch process with delay between requests
python run_flow_cloud_batch.py --count 50 --workers 5 --delay 0.1

# Custom tweaks for all requests
python run_flow_cloud_batch.py --count 10 --tweaks '{"TextInput-abc": {"input_value": "Batch processing"}}'

OUTPUT:
-------
The script provides:
- Real-time progress updates
- Individual request results
- Summary statistics (success rate, average response time, etc.)
- Error details for failed requests
"""

class BatchFlowRunner:
    def __init__(self, api_key, langflow_url, org_id, input_value="batch test", 
                 tweaks=None, output_type="chat", input_type="text", timeout=30):
        self.api_key = api_key
        self.langflow_url = langflow_url
        self.org_id = org_id
        self.input_value = input_value
        self.tweaks = tweaks
        self.output_type = output_type
        self.input_type = input_type
        self.timeout = timeout
        self.flow_url = langflow_url  # Use URL directly
        
        # Statistics
        self.lock = threading.Lock()
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.total_time = 0
        self.start_time = None
        self.results = []
        self.errors = []

    def log(self, message):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def run_single_request(self, request_id):
        """Run a single flow request"""
        payload = {
            "output_type": self.output_type,
            "input_type": self.input_type,
            "input_value": f"{self.input_value} (Request #{request_id})",
            "session_id": str(uuid.uuid4())  # Generate unique session ID for each request
        }
        
        if self.tweaks:
            payload["tweaks"] = self.tweaks
        
        headers = {
            "X-DataStax-Current-Org": self.org_id,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        request_start = time.time()
        
        try:
            response = requests.post(
                self.flow_url, 
                json=payload, 
                headers=headers,
                timeout=self.timeout
            )
            
            request_time = time.time() - request_start
            
            with self.lock:
                self.completed += 1
                self.total_time += request_time
                
                if response.status_code == 200:
                    self.successful += 1
                    result = {
                        'request_id': request_id,
                        'status': 'success',
                        'status_code': response.status_code,
                        'response_time': request_time,
                        'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    }
                    self.results.append(result)
                    print(f"✅ Request #{request_id}: SUCCESS ({request_time:.2f}s)")
                    
                else:
                    self.failed += 1
                    error_info = {
                        'request_id': request_id,
                        'status': 'failed',
                        'status_code': response.status_code,
                        'response_time': request_time,
                        'error': response.text
                    }
                    self.errors.append(error_info)
                    print(f"❌ Request #{request_id}: FAILED (Status: {response.status_code}, Time: {request_time:.2f}s)")
                    
        except requests.exceptions.RequestException as e:
            request_time = time.time() - request_start
            
            with self.lock:
                self.completed += 1
                self.failed += 1
                self.total_time += request_time
                
                error_info = {
                    'request_id': request_id,
                    'status': 'error',
                    'response_time': request_time,
                    'error': str(e)
                }
                self.errors.append(error_info)
                print(f"💥 Request #{request_id}: ERROR ({str(e)}, Time: {request_time:.2f}s)")

    def run_batch(self, count, workers, delay=0):
        """Run multiple requests in parallel"""
        self.log(f"🚀 Starting batch execution...")
        self.log(f"📊 Total requests: {count}")
        self.log(f"👥 Concurrent workers: {workers}")
        self.log(f"🌐 Flow URL: {self.flow_url}")
        self.log(f"🏢 Organization ID: {self.org_id}")
        self.log(f"📝 Input template: {self.input_value}")
        if delay > 0:
            self.log(f"⏱️ Delay between batches: {delay}s")
        
        self.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all requests
            futures = []
            for i in range(1, count + 1):
                future = executor.submit(self.run_single_request, i)
                futures.append(future)
                
                # Add delay if specified
                if delay > 0 and i % workers == 0:
                    time.sleep(delay)
            
            # Wait for completion and show progress
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log(f"💥 Unexpected error in request: {e}")
                
                # Show progress
                with self.lock:
                    progress = (self.completed / count) * 100
                    print(f"📈 Progress: {self.completed}/{count} ({progress:.1f}%) - ✅ {self.successful} | ❌ {self.failed}")

    def print_summary(self, count):
        """Print execution summary"""
        end_time = time.time()
        total_execution_time = end_time - self.start_time
        avg_response_time = self.total_time / count if count > 0 else 0
        success_rate = (self.successful / count) * 100 if count > 0 else 0
        requests_per_second = count / total_execution_time if total_execution_time > 0 else 0
        
        self.log("=" * 60)
        self.log("📊 BATCH EXECUTION SUMMARY")
        self.log("=" * 60)
        self.log(f"📈 Total Requests: {count}")
        self.log(f"✅ Successful: {self.successful}")
        self.log(f"❌ Failed: {self.failed}")
        self.log(f"📊 Success Rate: {success_rate:.1f}%")
        self.log(f"⏱️ Total Execution Time: {total_execution_time:.2f}s")
        self.log(f"⚡ Requests per Second: {requests_per_second:.2f}")
        self.log(f"📏 Average Response Time: {avg_response_time:.2f}s")
        
        if self.errors:
            self.log("=" * 60)
            self.log("❌ ERROR DETAILS")
            self.log("=" * 60)
            for error in self.errors[:10]:  # Show first 10 errors
                self.log(f"Request #{error['request_id']}: {error.get('error', 'Unknown error')}")
            
            if len(self.errors) > 10:
                self.log(f"... and {len(self.errors) - 10} more errors")

def main():
    """Main function to run batch flow execution."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run multiple Langflow Cloud requests simultaneously")
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of requests to send (required)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)"
    )
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_URL"),
        help="Complete Langflow Cloud API endpoint URL (default: from LANGFLOW_URL env var)"
    )
    parser.add_argument(
        "--langflow-token",
        default=os.getenv("LANGFLOW_TOKEN"),
        help="Langflow Application Token (default: from LANGFLOW_TOKEN env var)"
    )
    parser.add_argument(
        "--langflow-org",
        default=os.getenv("LANGFLOW_CURRENT_ORG"),
        help="Langflow Organization ID (default: from LANGFLOW_CURRENT_ORG env var)"
    )
    parser.add_argument(
        "--flow-id",
        help="Flow ID (optional, used to build URL if LANGFLOW_URL is a base URL)"
    )
    parser.add_argument(
        "--input-value",
        default="batch test",
        help="Input value template for all requests (default: 'batch test')"
    )
    parser.add_argument(
        "--tweaks",
        help="Custom tweaks as JSON string (optional)"
    )
    parser.add_argument(
        "--output-type",
        default="chat",
        help="Output type (default: 'chat')"
    )
    parser.add_argument(
        "--input-type",
        default="text",
        help="Input type (default: 'text')"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Delay between request batches in seconds (default: 0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Build URL based on what's provided
    langflow_url = args.langflow_url
    
    # If flow-id is provided, build the complete URL
    if args.flow_id:
        if langflow_url and "/api/v1/run/" not in langflow_url:
            # URL is a base URL, construct the full endpoint
            langflow_url = langflow_url.rstrip('/')
            langflow_url = f"{langflow_url}/api/v1/run/{args.flow_id}"
            print(f"🔨 Built URL: {langflow_url}")
        elif not langflow_url:
            print("❌ Error: Cannot use --flow-id without --langflow-url or LANGFLOW_URL env var.")
            print("Please provide a base URL to build the complete endpoint.")
            sys.exit(1)
    
    # Validation
    if args.count <= 0:
        print("❌ Error: Count must be greater than 0")
        sys.exit(1)
        
    if args.workers <= 0:
        print("❌ Error: Workers must be greater than 0")
        sys.exit(1)
    
    # Check if URL is available
    if not langflow_url:
        print("❌ Error: LANGFLOW_URL environment variable not set.")
        print("Please set the API endpoint URL in the .env file or use --langflow-url parameter")
        print("Example (complete): https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID/api/v1/run/YOUR_FLOW_ID")
        print("Example (base): https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID (use with --flow-id)")
        sys.exit(1)
    
    if not args.langflow_token:
        print("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        print("Please set your Application Token in the .env file or use --langflow-token parameter")
        sys.exit(1)
    
    if not args.langflow_org:
        print("❌ Error: LANGFLOW_CURRENT_ORG environment variable not set.")
        print("Please set your Organization ID in the .env file or use --langflow-org parameter")
        sys.exit(1)
    
    # Parse tweaks if provided
    tweaks = None
    if args.tweaks:
        try:
            tweaks = json.loads(args.tweaks)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing tweaks JSON: {e}")
            print("Please ensure tweaks are in valid JSON format")
            sys.exit(1)
    
    try:
        # Create runner and execute batch
        runner = BatchFlowRunner(
            args.langflow_token,
            langflow_url,
            args.langflow_org,
            args.input_value,
            tweaks,
            args.output_type,
            args.input_type,
            args.timeout
        )
        
        # Run batch
        runner.run_batch(args.count, args.workers, args.delay)
        
        # Print summary
        runner.print_summary(args.count)
        
        print("\n🎉 Batch execution completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 