import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

"""
Run Flow Script for Langflow using OpenAI SDK
============================================

This script runs a specified flow in Langflow using the OpenAI SDK client.
It provides a compatible interface with OpenAI's SDK for running Langflow flows.

USAGE:
------
Basic usage:
    python run_flow_openai.py

With custom parameters:
    python run_flow_openai.py --flow-id YOUR_FLOW_ID --input "Process this text"

With custom Langflow server:
    python run_flow_openai.py --langflow-url http://your-server:3000 --langflow-token your_token

ENVIRONMENT VARIABLES:
---------------------
Create a .env file with the following variables:
    LANGFLOW_URL=http://localhost:3000
    LANGFLOW_TOKEN=your_api_token_here
    FLOW_ID=your_default_flow_id
    OPEN_AI_KEY=your_openai_key_here (optional, uses dummy-api-key if not provided)

COMMAND LINE ARGUMENTS:
----------------------
    --langflow-url      Langflow server URL (default: LANGFLOW_URL env var or http://localhost:3000)
    --langflow-token    Langflow API token (default: LANGFLOW_TOKEN env var)
    --flow-id           Flow ID to run (default: FLOW_ID env var)
    --input             Input value for the flow (default: "hello world!")
    --open-ai-key       OpenAI API key (default: OPEN_AI_KEY env var or "dummy-api-key")

EXAMPLES:
--------
# Run flow with default settings
python run_flow_openai.py

# Run with custom input
python run_flow_openai.py --input "Analyze this text"

# Use a different flow
python run_flow_openai.py --flow-id "abc123-def456-ghi789"

# Connect to remote Langflow instance
python run_flow_openai.py --langflow-url https://my-langflow.com --langflow-token sk_token_here

# Run with custom input
python run_flow_openai.py --input "There is an event that happens on the second wednesday of every month. What are the event dates in 2026?"

ERROR HANDLING:
--------------
The script provides detailed error messages for common issues:
- Invalid API tokens
- Network connectivity problems
- Flow execution errors
- Missing required parameters

Check the console output for specific error details and suggestions.
"""

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_flow_openai(langflow_url, langflow_token, flow_id, input_value="hello world!", open_ai_key="dummy-api-key"):
    """
    Run the Langflow flow using OpenAI SDK client.
    
    Args:
        langflow_url (str): Langflow server URL
        langflow_token (str): Langflow API token
        flow_id (str): The flow ID to run
        input_value (str): Input value for the flow
        open_ai_key (str): OpenAI API key (required by SDK but not used by Langflow)
    """
    
    # Ensure URL doesn't have double slashes
    langflow_url = langflow_url.rstrip('/')
    base_url = f"{langflow_url}/api/v1/"
    
    try:
        log("🚀 Initializing OpenAI client for Langflow...")
        log(f"🌐 Base URL: {base_url}")
        log(f"🎯 Flow ID: {flow_id}")
        log(f"📝 Input: {input_value}")
        
        # Initialize OpenAI client with Langflow configuration
        client = OpenAI(
            base_url=base_url,
            default_headers={"x-api-key": langflow_token},
            api_key=open_ai_key  # Required by OpenAI SDK but not used by Langflow
        )
        
        log("✅ Client initialized successfully!")
        log("🚀 Running flow...")
        
        # Execute the flow using OpenAI SDK
        response = client.responses.create(
            model=flow_id,
            input=input_value,
        )
        
        log("✅ Flow executed successfully!")
        log("📄 Response:")
        
        # Print the output text
        if hasattr(response, 'output_text'):
            print(response.output_text)
            return response.output_text
        else:
            log(f"📄 Full response: {response}")
            return response
        
    except Exception as e:
        log(f"❌ Error executing flow: {e}")
        if hasattr(e, 'response'):
            log(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            log(f"Response text: {getattr(e.response, 'text', 'N/A')}")
        raise

def main():
    """Main function to run the flow."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run Langflow flow using OpenAI SDK")
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
        "--input",
        default="hello world!",
        help="Input value for the flow (default: 'hello world!')"
    )
    parser.add_argument(
        "--open-ai-key",
        default=os.getenv("OPEN_AI_KEY", "dummy-api-key"),
        help="OpenAI API key (default: from OPEN_AI_KEY env var or 'dummy-api-key')"
    )
    
    args = parser.parse_args()
    
    # Check if API token is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API token in the .env file or use --langflow-token parameter")
        sys.exit(1)
    
    # Check if flow ID is available
    if not args.flow_id:
        log("❌ Error: FLOW_ID not specified.")
        log("Please set FLOW_ID in the .env file or use --flow-id parameter")
        sys.exit(1)
    
    try:
        log("🎯 Starting flow execution...")
        
        result = run_flow_openai(
            args.langflow_url,
            args.langflow_token,
            args.flow_id,
            args.input,
            args.open_ai_key
        )
        
        log("🎉 Flow execution completed!")
        
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()

