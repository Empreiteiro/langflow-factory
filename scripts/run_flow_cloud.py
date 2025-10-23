import requests
import os
import sys
import argparse
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv 

"""
Run Flow Script for Langflow Cloud
===================================

This script runs a specified flow in Langflow Cloud without requiring file uploads.
It allows you to execute flows with custom parameters and tweaks.

USAGE:
------
Basic usage (with URL in .env file):
    python run_flow_cloud.py

With custom input:
    python run_flow_cloud.py --input-value "Process this text"

With complete URL:
    python run_flow_cloud.py --langflow-url "https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG/api/v1/run/YOUR_FLOW" --input-value "hello"

ENVIRONMENT VARIABLES:
---------------------
Create a .env file with the following variables:

Option 1 - Complete URL (recommended):
    LANGFLOW_URL=https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID/api/v1/run/YOUR_FLOW_ID
    LANGFLOW_TOKEN=your_application_token_here
    LANGFLOW_CURRENT_ORG=your_org_id_here

Option 2 - Base URL (use with --flow-id parameter):
    LANGFLOW_URL=https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID
    LANGFLOW_TOKEN=your_application_token_here
    LANGFLOW_CURRENT_ORG=your_org_id_here

COMMAND LINE ARGUMENTS:
----------------------
    --langflow-url      Complete API endpoint URL or base URL (default: LANGFLOW_URL env var)
    --langflow-token    Langflow Application Token (default: LANGFLOW_TOKEN env var)
    --langflow-org      Langflow Organization ID (default: LANGFLOW_CURRENT_ORG env var)
    --flow-id           Flow ID (optional, builds URL if base URL is provided)
    --input-value       Input value for the flow (default: "hello world!")
    --tweaks            Custom tweaks as JSON string (optional)
    --output-type       Output type (default: "chat")
    --input-type        Input type (default: "text")
    --session-id        Session ID (optional, auto-generated if not provided)

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
# Run flow with default settings (complete URL in .env)
python run_flow_cloud.py

# Run with custom input
python run_flow_cloud.py --input-value "Analyze this text"

# Use a different flow (with base URL in .env)
python run_flow_cloud.py --flow-id "abc123-def456-ghi789"

# Use complete URL
python run_flow_cloud.py --langflow-url "https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG/api/v1/run/YOUR_FLOW"

# Run with custom tweaks
python run_flow_cloud.py --input-value "Hello" --tweaks '{"TextInput-xyz": {"input_value": "Custom input"}}'

# Complete example with base URL + flow-id
python run_flow_cloud.py --langflow-url "https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG" --flow-id "YOUR_FLOW_ID" --langflow-token your_token --langflow-org your_org_id --input-value "Hello"

ERROR HANDLING:
--------------
The script provides detailed error messages for common issues:
- Invalid API tokens
- Network connectivity problems
- Flow execution errors
- Invalid JSON in tweaks

Check the console output for specific error details and suggestions.
"""

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_flow(api_key, langflow_url, org_id, input_value="hello world!", tweaks=None, output_type="chat", input_type="text", session_id=None):
    """
    Run the Langflow Cloud flow with specified parameters.
    
    Args:
        api_key (str): Langflow Application Token
        langflow_url (str): Complete Langflow Cloud API endpoint URL
        org_id (str): Organization ID
        input_value (str): Input value for the flow
        tweaks (dict): Custom tweaks for components
        output_type (str): Output type (default: "chat")
        input_type (str): Input type (default: "text")
        session_id (str): Session ID (optional, auto-generated if not provided)
    """
    
    # Use the URL directly from env without modifications
    flow_url = langflow_url
    
    payload = {
        "output_type": output_type,
        "input_type": input_type,
        "input_value": input_value
    }
    
    # Add session_id (generate if not provided)
    if session_id:
        payload["session_id"] = session_id
    else:
        payload["session_id"] = str(uuid.uuid4())
    
    # Add tweaks if provided
    if tweaks:
        payload["tweaks"] = tweaks
        log(f"📝 Using custom tweaks: {json.dumps(tweaks, indent=2)}")
    
    headers = {
        "X-DataStax-Current-Org": org_id,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        log("🚀 Running flow...")
        log(f"🌐 URL: {flow_url}")
        log(f"🏢 Organization ID: {org_id}")
        log(f"🔑 Session ID: {payload['session_id']}")
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
    
    parser = argparse.ArgumentParser(description="Run Langflow Cloud flow")
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
        default="hello world!",
        help="Input value for the flow (default: 'hello world!')"
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
        "--session-id",
        help="Session ID (optional, auto-generated if not provided)"
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
            log(f"🔨 Built URL: {langflow_url}")
        elif not langflow_url:
            log("❌ Error: Cannot use --flow-id without --langflow-url or LANGFLOW_URL env var.")
            log("Please provide a base URL to build the complete endpoint.")
            sys.exit(1)
    
    # Check if URL is available
    if not langflow_url:
        log("❌ Error: LANGFLOW_URL environment variable not set.")
        log("Please set the API endpoint URL in the .env file or use --langflow-url parameter")
        log("Example (complete): https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID/api/v1/run/YOUR_FLOW_ID")
        log("Example (base): https://aws-us-west-2.langflow-test.datastax.com/lf/YOUR_ORG_ID (use with --flow-id)")
        sys.exit(1)
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your Application Token in the .env file or use --langflow-token parameter")
        sys.exit(1)
    
    # Check if organization ID is available
    if not args.langflow_org:
        log("❌ Error: LANGFLOW_CURRENT_ORG environment variable not set.")
        log("Please set your Organization ID in the .env file or use --langflow-org parameter")
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
        
        result = run_flow(
            args.langflow_token, 
            langflow_url,
            args.langflow_org,
            args.input_value,
            tweaks,
            args.output_type,
            args.input_type,
            args.session_id
        )
        
        log("🎉 Flow execution completed!")
        
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 