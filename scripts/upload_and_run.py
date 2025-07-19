import requests
import os
import sys
import argparse
import mimetypes
from datetime import datetime
from dotenv import load_dotenv 

"""
Upload and Run Script for Langflow
==================================

This script uploads a file to Langflow and then runs a specified flow with that file.
It supports any file type and automatically detects the MIME type.

USAGE:
------
Basic usage:
    python upload_and_run.py path/to/your/file.pdf

With custom parameters:
    python upload_and_run.py document.pdf --flow-id YOUR_FLOW_ID --input-value "Process this document"

With custom Langflow server:
    python upload_and_run.py file.txt --langflow-url http://your-server:3000 --langflow-token your_token

ENVIRONMENT VARIABLES:
---------------------
Create a .env file with the following variables:
    LANGFLOW_URL=http://localhost:3000
    LANGFLOW_TOKEN=your_api_token_here
    FLOW_ID=your_default_flow_id

COMMAND LINE ARGUMENTS:
----------------------
    file_path           Path to the file to upload (required)
    --langflow-url      Langflow server URL (default: LANGFLOW_URL env var or http://localhost:3000)
    --langflow-token    Langflow API token (default: LANGFLOW_TOKEN env var)
    --flow-id           Flow ID to run (default: FLOW_ID env var)
    --input-value       Input value for the flow (default: "hello world!")

CUSTOMIZING TWEAKS FOR YOUR FLOW:
---------------------------------
The script currently includes a basic tweaks configuration that sets the file path
for a component named "File-hftNJ". You may need to modify this for your specific flow.

To customize tweaks for your flow:

1. Find your component IDs:
   - Open your flow in Langflow
   - Check the component IDs in the flow editor
   - Component IDs typically look like "ComponentName-ABC12"

2. Modify the payload in the run_flow_with_file() function:
   
   Example tweaks for different components:
   
   # For a Text Input component
   "tweaks": {
       "TextInput-xyz123": {
           "input_value": "Your custom text here"
       },
       "File-hftNJ": {
           "path": [file_path_from_upload]
       }
   }
   
   # For a custom component with parameters
   "tweaks": {
       "CustomComponent-abc456": {
           "parameter1": "value1",
           "parameter2": "value2",
           "user_id": "user123"
       },
       "File-hftNJ": {
           "path": [file_path_from_upload]
       }
   }
   
   # For multiple file inputs
   "tweaks": {
       "File-input1": {
           "path": [file_path_from_upload]
       },
       "File-input2": {
           "path": ["path/to/another/file"]
       }
   }

3. Common component types and their parameters:
   
   - File components: {"path": [file_path]}
   - Text Input: {"input_value": "text"}
   - Number Input: {"input_value": 123}
   - Dropdown: {"input_value": "selected_option"}
   - Custom Components: Check your component's specific parameters

4. To find the exact component IDs and parameter names:
   - Export your flow as JSON from Langflow
   - Look at the "data" section to see component IDs and available parameters
   - Or use the Langflow API to inspect the flow structure

EXAMPLES:
--------
# Upload a PDF and run with default settings
python upload_and_run.py document.pdf

# Upload an image with custom input
python upload_and_run.py image.jpg --input-value "Analyze this image"

# Use a different flow
python upload_and_run.py data.csv --flow-id "abc123-def456-ghi789"

# Connect to remote Langflow instance
python upload_and_run.py file.txt --langflow-url https://my-langflow.com --langflow-token sk_token_here

SUPPORTED FILE TYPES:
--------------------
Documents: PDF, DOC, DOCX, TXT, CSV, JSON, XML, HTML
Images: PNG, JPG, JPEG, GIF, BMP, SVG
Audio: MP3
Video: MP4, AVI, MOV
Archives: ZIP, RAR, 7Z, TAR, GZ, BZ2
And many more...

ERROR HANDLING:
--------------
The script provides detailed error messages for common issues:
- Missing files
- Invalid API tokens
- Network connectivity problems
- Flow execution errors

Check the console output for specific error details and suggestions.
"""

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_mime_type(file_extension):
    """
    Get MIME type based on file extension.
    
    Args:
        file_extension (str): File extension (e.g., '.pdf', '.txt')
    
    Returns:
        str: MIME type for the file extension
    """
    # Common MIME types mapping
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.mp3': 'audio/mpeg',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.zip': 'application/zip',
        '.rar': 'application/vnd.rar',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.bz2': 'application/x-bzip2'
    }
    
    # Try to get MIME type from our mapping first
    if file_extension in mime_types:
        return mime_types[file_extension]
    
    # Fallback to Python's mimetypes module
    mime_type, _ = mimetypes.guess_type(f"file{file_extension}")
    return mime_type

def upload_file_v2(file_path, api_key, langflow_url):
    """
    Upload any file to Langflow using the v2 files API endpoint.
    
    Args:
        file_path (str): Path to the file to upload
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
    
    Returns:
        dict: Response from the API containing file metadata
    """
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension and determine MIME type
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type = get_mime_type(file_extension)
    
    if not mime_type:
        log(f"⚠️  Warning: Could not determine MIME type for {file_extension}, using 'application/octet-stream'")
        mime_type = 'application/octet-stream'
    
    upload_url = f"{langflow_url}/api/v2/files"
    
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    with open(file_path, 'rb') as file:
        files = {
            'file': (os.path.basename(file_path), file, mime_type)
        }
        
        try:
            response = requests.post(
                upload_url,
                headers=headers,
                files=files
            )
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log(f"Error uploading file: {e}")
            if hasattr(e, 'response') and e.response is not None:
                log(f"Response status: {e.response.status_code}")
                log(f"Response text: {e.response.text}")
            raise

def run_flow_with_file(file_path_from_upload, api_key, langflow_url, flow_id, input_value="hello world!"):
    """
    Run the Langflow flow with the uploaded file.
    
    Args:
        file_path_from_upload (str): The path returned from the upload API
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
        flow_id (str): The flow ID to run
        input_value (str): Input value for the flow
    """
    
    flow_url = f"{langflow_url}/api/v1/run/{flow_id}"
    
    payload = {
        "output_type": "text",
        "input_type": "text",
        "input_value": input_value,
        "tweaks": {
            "File-hftNJ": {
                "path": [file_path_from_upload]
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    try:
        log("🚀 Running flow with uploaded file...")
        
        response = requests.request(
            "POST", flow_url, json=payload, headers=headers
        )
        
        log(f"Status Code: {response.status_code}")
        log(f"Response Headers: {response.headers}")
        
        response.raise_for_status()
        
        log("✅ Flow executed successfully!")
        log("📄 Response:")
        log(response.text)
        
    except requests.exceptions.RequestException as e:
        log(f"❌ Error making API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Response status: {e.response.status_code}")
            log(f"Response text: {e.response.text}")

def main():
    """Main function to upload file and run flow."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Upload file and run Langflow flow")
    parser.add_argument(
        "file_path",
        help="Path to the file to upload"
    )
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
        default=os.getenv("FLOW_ID", "7955e39d-7fe0-44f3-9de2-fe5b2b9ba479"),
        help="Flow ID to run (default: from FLOW_ID env var)"
    )
    parser.add_argument(
        "--input-value",
        default="hello world!",
        help="Input value for the flow (default: 'hello world!')"
    )
    
    args = parser.parse_args()
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API key in the .env file or use --langflow-token parameter")
        return
    
    try:
        log("📤 Step 1: Uploading file...")
        
        result = upload_file_v2(args.file_path, args.langflow_token, args.langflow_url)
        
        log("✅ File uploaded successfully!")
        log(f"📄 File ID: {result['id']}")
        log(f"📁 File Name: {result['name']}")
        log(f"📂 File Path: {result['path']}")
        log(f"📏 File Size: {result['size']} bytes")
        
        file_path_for_api = result['path']
        log(f"🎯 Using path: {file_path_for_api}")
        
        log("\n" + "="*50)
        log("📤 Step 2: Running flow with uploaded file...")
        
        run_flow_with_file(
            file_path_for_api, 
            args.langflow_token, 
            args.langflow_url, 
            args.flow_id, 
            args.input_value
        )
        
    except FileNotFoundError as e:
        log(f"❌ {e}")
        sys.exit(1)
    except ValueError as e:
        log(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 