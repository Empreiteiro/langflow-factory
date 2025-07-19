import requests
import os
import sys
import argparse
import mimetypes
from datetime import datetime
from dotenv import load_dotenv

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
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension and determine MIME type
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type = get_mime_type(file_extension)
    
    if not mime_type:
        log(f"⚠️  Warning: Could not determine MIME type for {file_extension}, using 'application/octet-stream'")
        mime_type = 'application/octet-stream'
    
    # API endpoint for v2 file upload
    upload_url = f"{langflow_url}/api/v2/files"
    
    # Headers required for v2 API
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    # Prepare the file for upload
    with open(file_path, 'rb') as file:
        files = {
            'file': (os.path.basename(file_path), file, mime_type)
        }
        
        try:
            # Send POST request to upload file
            response = requests.post(
                upload_url,
                headers=headers,
                files=files
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Return the response JSON
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error uploading file: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            raise

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

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def main():
    """Main function to handle command line arguments and execute upload."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Upload any file to Langflow")
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
    
    args = parser.parse_args()
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API key in the .env file or use --langflow-token parameter")
        sys.exit(1)
    
    try:
        log("Starting file upload...")
        # Upload the file
        result = upload_file_v2(args.file_path, args.langflow_token, args.langflow_url)
        
        # Get the file_id from the result
        file_id = result['id']
        user_id = result['path'].split('/')[0]
        file_extension = os.path.splitext(args.file_path)[1].lower()
        
        print(f"\n🎯 File ID for API usage: {file_id}")
        print(f"🎯 User ID for API usage: {user_id}")
        print(f"🎯 Correct path format: {user_id}/{file_id}{file_extension}")
        
        log("✅ File uploaded successfully!")
        log(f"📄 File ID: {result['id']}")
        log(f"📁 File Name: {result['name']}")
        log(f"📂 File Path: {result['path']}")
        log(f"📏 File Size: {result['size']} bytes")
        log(f"🔧 Provider: {result['provider']}")
        
        # Extract user_id from path (first part before /)
        user_id = result['path'].split('/')[0]
        file_id = result['id']
        
        log(f"\n🔑 User ID: {user_id}")
        log(f"🆔 File ID: {file_id}")
        
        # Generate the correct path format for API usage
        correct_path = f"{user_id}/{file_id}{file_extension}"
        log(f"📋 Correct Path for API: {correct_path}")
        
        log("\n💡 To use this file in your flow, include it in the tweaks section:")
        log(f"   'File-COMPONENT_ID': {{")
        log(f"       'path': ['{correct_path}']")
        log(f"   }}")
        
        # Return the file_id for programmatic use
        return file_id
        
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