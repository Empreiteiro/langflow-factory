import os
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import requests

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
    --stream            Enable streaming response (default: False)

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

# Run with streaming enabled
python run_flow_openai.py --input "Tell me a story" --stream

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

def run_flow_openai(langflow_url, langflow_token, flow_id, input_value="hello world!", open_ai_key="dummy-api-key", stream=False, debug=False):
    """
    Run the Langflow flow using OpenAI SDK client.
    
    Args:
        langflow_url (str): Langflow server URL
        langflow_token (str): Langflow API token
        flow_id (str): The flow ID to run
        input_value (str): Input value for the flow
        open_ai_key (str): OpenAI API key (required by SDK but not used by Langflow)
        stream (bool): Whether to stream the response
        debug (bool): Enable debug mode to see raw streaming data
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
        
        # Execute the flow using OpenAI SDK Responses API
        # According to https://docs.langflow.org/api-openai-responses
        # Since the OpenAI SDK doesn't have a 'responses' attribute, we use requests
        # to call the /responses endpoint directly, using the same base URL and headers
        # configured in the OpenAI client
        
        # Use requests with the same configuration as the OpenAI client
        responses_url = f"{base_url}responses"
        
        if stream:
            # Streaming mode
            log("🌊 Streaming response:")
            log("=" * 50)
            
            response = requests.post(
                responses_url,
                json={
                    "model": flow_id,
                    "input": input_value,
                    "stream": True
                },
                headers={"x-api-key": langflow_token, "Content-Type": "application/json"},
                stream=True
            )
            response.raise_for_status()
            
            # Process streaming response
            # Format: Server-Sent Events (SSE) with "event:" and "data:" lines
            # Format: {"id": "...", "object": "response.chunk", "delta": {...}, "status": "completed"}
            full_response = ""
            chunk_count = 0
            empty_line_count = 0
            current_event = None
            
            if debug:
                log("🔍 Starting to read stream lines...")
            
            for line in response.iter_lines():
                if debug:
                    log(f"🔍 Received line (raw bytes): {line}")
                
                if line:
                    try:
                        # Decode the line
                        line_str = line.decode('utf-8')
                        
                        # Handle Server-Sent Events (SSE) format
                        # Lines can be "event: ..." or "data: ..."
                        if line_str.startswith("event: "):
                            # Store the event type
                            current_event = line_str[7:].strip()
                            if debug:
                                log(f"📌 Event type: {current_event}")
                            continue
                        
                        elif line_str.startswith("data: "):
                            # Remove "data: " prefix
                            json_str = line_str[6:]  # Remove "data: "
                            
                            # Debug: Print raw chunk for analysis
                            if debug:
                                log(f"🔍 Raw line ({chunk_count}): {line_str}")
                            
                            # Check for [DONE] marker
                            if json_str.strip() == "[DONE]":
                                if debug:
                                    log("✅ Received [DONE] marker")
                                log("\n" + "=" * 50)
                                log("✅ Streaming completed!")
                                if debug:
                                    log(f"📝 Total chunks received: {chunk_count}")
                                    log(f"📝 Full response length: {len(full_response)}")
                                return {"text": full_response}
                            
                            # Parse JSON chunk
                            chunk_data = json.loads(json_str)
                            chunk_count += 1
                            
                            if debug:
                                log(f"📋 Parsed chunk: {json.dumps(chunk_data, indent=2)}")
                            
                            # Check if it's a response.chunk object
                            if chunk_data.get("object") == "response.chunk":
                                delta = chunk_data.get("delta", {})
                            
                                if debug:
                                    log(f"📋 Delta: {json.dumps(delta, indent=2)}")
                                
                                # Extract text from delta
                                # Delta can contain various fields like "content", "text", etc.
                                text = ""
                                
                                if isinstance(delta, dict):
                                    # Try different ways to extract text
                                    # 1. Direct content field (most common in Langflow)
                                    text = delta.get("content", "")
                                    
                                    # 2. Direct text field
                                    if not text:
                                        text = delta.get("text", "")
                                    
                                    # 2. If delta has nested content array
                                    if not text and "content" in delta:
                                        content = delta["content"]
                                        if isinstance(content, list) and len(content) > 0:
                                            for item in content:
                                                if isinstance(item, dict):
                                                    text = item.get("text", "") or item.get("content", "") or text
                                                    if text:
                                                        break
                                        elif isinstance(content, str):
                                            text = content
                                    
                                    # 3. Check for output array structure
                                    if not text and "output" in delta:
                                        output = delta["output"]
                                        if isinstance(output, list) and len(output) > 0:
                                            for item in output:
                                                if isinstance(item, dict):
                                                    if "text" in item:
                                                        text = item["text"]
                                                        break
                                                    elif "content" in item:
                                                        content = item["content"]
                                                        if isinstance(content, list):
                                                            for c in content:
                                                                if isinstance(c, dict) and "text" in c:
                                                                    text = c["text"]
                                                                    break
                                                        elif isinstance(content, str):
                                                            text = content
                                                        if text:
                                                            break
                                    
                                    if debug and text:
                                        log(f"✅ Extracted text: '{text}'")
                                    
                                    if text:
                                        print(text, end="", flush=True)
                                        full_response += text
                                
                                # Check if streaming is completed
                                status = chunk_data.get("status")
                                if debug:
                                    log(f"📊 Status: {status}")
                                
                                if status == "completed":
                                    log("\n" + "=" * 50)
                                    log("✅ Streaming completed!")
                                    if debug:
                                        log(f"📝 Total chunks received: {chunk_count}")
                                        log(f"📝 Full response length: {len(full_response)}")
                                    return {"text": full_response}
                            
                            # Handle other event types that might contain text
                            elif chunk_data.get("type"):
                                event_type = chunk_data.get("type")
                                
                                # Check for message content in various event types
                                if "item" in chunk_data:
                                    item = chunk_data["item"]
                                    if isinstance(item, dict):
                                        # Check for text in item
                                        if "text" in item:
                                            text = item["text"]
                                            if text:
                                                print(text, end="", flush=True)
                                                full_response += text
                                                if debug:
                                                    log(f"✅ Extracted text from item: '{text}'")
                                        
                                        # Check for content in item
                                        if "content" in item:
                                            content = item["content"]
                                            if isinstance(content, str) and content:
                                                print(content, end="", flush=True)
                                                full_response += content
                                                if debug:
                                                    log(f"✅ Extracted content from item: '{content}'")
                                            elif isinstance(content, list):
                                                for c in content:
                                                    if isinstance(c, dict) and "text" in c:
                                                        text = c["text"]
                                                        if text:
                                                            print(text, end="", flush=True)
                                                            full_response += text
                                                            if debug:
                                                                log(f"✅ Extracted text from content array: '{text}'")
                                
                                # Check for text in delta for function call arguments
                                if "delta" in chunk_data and isinstance(chunk_data["delta"], str):
                                    # Delta might be a JSON string
                                    try:
                                        delta_obj = json.loads(chunk_data["delta"])
                                        if isinstance(delta_obj, dict) and "text" in delta_obj:
                                            text = delta_obj["text"]
                                            if text:
                                                print(text, end="", flush=True)
                                                full_response += text
                                    except:
                                        pass
                                
                                if debug:
                                    log(f"📌 Processed event type: {event_type}")
                        
                        else:
                            if debug:
                                log(f"⚠️  Unknown object type: {chunk_data.get('object')}")
                    
                    except json.JSONDecodeError as e:
                        # Skip invalid JSON lines but log them in debug mode
                        if debug:
                            log(f"⚠️  Invalid JSON line: {line_str}")
                            log(f"⚠️  Error: {e}")
                        continue
                    except Exception as e:
                        log(f"⚠️  Error processing stream line: {e}")
                        if debug:
                            import traceback
                            log(f"⚠️  Traceback: {traceback.format_exc()}")
                        continue
                else:
                    empty_line_count += 1
                    if debug:
                        log(f"⚠️  Empty line received (count: {empty_line_count})")
                
                if debug and chunk_count == 0 and empty_line_count > 5:
                    log("⚠️  Warning: Receiving many empty lines, stream might not be working correctly")
            
            log("\n" + "=" * 50)
            log("✅ Streaming completed!")
            if debug:
                log(f"📝 Total chunks received: {chunk_count}")
                log(f"📝 Full response length: {len(full_response)}")
            return {"text": full_response}
            
            log("\n" + "=" * 50)
            log("✅ Streaming completed!")
            return {"text": full_response}
        
        else:
            # Non-streaming mode
            response = requests.post(
                responses_url,
                json={
                    "model": flow_id,
                    "input": input_value,
                    "stream": False
                },
                headers={"x-api-key": langflow_token, "Content-Type": "application/json"}
            )
            response.raise_for_status()
            response_data = response.json()
            
            log("✅ Flow executed successfully!")
            log("📄 Response:")
            
            # Extract output_text from response according to Langflow documentation
            # Response format: {"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}
            output_text = None
            
            if isinstance(response_data, dict):
                # Try to extract text from the response structure
                if "output_text" in response_data:
                    output_text = response_data["output_text"]
                elif "output" in response_data:
                    output = response_data["output"]
                    if isinstance(output, list):
                        for item in output:
                            if isinstance(item, dict):
                                # Check for content array with text
                                if "content" in item and isinstance(item["content"], list):
                                    for content_item in item["content"]:
                                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                            output_text = content_item.get("text", "")
                                            break
                                # Check for direct text field
                                elif "text" in item:
                                    output_text = item["text"]
                                    break
                                # Check for message with text
                                elif item.get("type") == "message" and "text" in item:
                                    output_text = item["text"]
                                    break
                    
                    if not output_text and isinstance(output, list) and len(output) > 0:
                        # Try to get text from first item
                        first_item = output[0]
                        if isinstance(first_item, dict):
                            if "text" in first_item:
                                output_text = first_item["text"]
            
            if output_text:
                print(output_text)
                return output_text
            else:
                # Print full JSON response if text extraction failed
                log(json.dumps(response_data, indent=2, ensure_ascii=False))
                return response_data
        
    except Exception as e:
        log(f"❌ Error executing flow: {e}")
        if hasattr(e, 'response'):
            log(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            log(f"Response text: {getattr(e.response, 'text', 'N/A')}")
        import traceback
        log(f"Full traceback: {traceback.format_exc()}")
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
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming response (default: False)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode to see raw streaming data (default: False)"
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
            args.open_ai_key,
            args.stream,
            args.debug
        )
        
        log("🎉 Flow execution completed!")
        
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()

