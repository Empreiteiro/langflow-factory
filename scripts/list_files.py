import requests
import os
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

def list_files_v2(api_key, langflow_url):
    """
    List all files associated with your user account using the v2 files API.
    
    Args:
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
    
    Returns:
        list: List of file metadata dictionaries
    """
    
    # API endpoint for v2 file listing
    list_url = f"{langflow_url}/api/v2/files"
    
    # Headers required for v2 API
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    try:
        # Send GET request to list files
        response = requests.get(list_url, headers=headers)
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Return the response JSON
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error listing files: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        raise

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def display_files(files):
    """
    Display files in a formatted way.
    
    Args:
        files (list): List of file metadata dictionaries
    """
    if not files:
        log("📁 No files found in your account.")
        return
    
    log(f"📁 Found {len(files)} file(s) in your account:")
    print("=" * 80)
    
    for i, file in enumerate(files, 1):
        print(f"\n📄 File #{i}")
        print(f"   🆔 ID: {file.get('id', 'N/A')}")
        print(f"   📁 Name: {file.get('name', 'N/A')}")
        print(f"   📂 Path: {file.get('path', 'N/A')}")
        print(f"   📏 Size: {file.get('size', 'N/A')} bytes")
        print(f"   🔧 Provider: {file.get('provider', 'N/A')}")
        
        # Extract user_id and file_id from path for easy reference
        path = file.get('path', '')
        if '/' in path:
            user_id = path.split('/')[0]
            file_id = path.split('/')[1].split('.')[0] if '.' in path.split('/')[1] else path.split('/')[1]
            print(f"   🔑 User ID: {user_id}")
            print(f"   🆔 File ID: {file_id}")
        
        print("-" * 40)

def main():
    """Main function to list files."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="List files from Langflow")
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
        "--export-json",
        action="store_true",
        help="Export files list to JSON file"
    )
    parser.add_argument(
        "--output-file",
        default="files_list.json",
        help="Output file name for JSON export (default: files_list.json)"
    )
    
    args = parser.parse_args()
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API key in the .env file or use --langflow-token parameter")
        return
    
    try:
        log("🔍 Listing files from Langflow...")
        files = list_files_v2(args.langflow_token, args.langflow_url)
        
        # Display files in a formatted way
        display_files(files)
        
        # Save to JSON file for reference
        if args.export_json or files:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(files, f, indent=2, ensure_ascii=False)
            log(f"💾 File list saved to '{args.output_file}'")
        
        # Show usage examples
        if files:
            log("\n💡 Usage examples:")
            log("   To use a file in your flow, copy the path and use it in tweaks:")
            for file in files:
                path = file.get('path', '')
                if path:
                    log(f"   'File-COMPONENT_ID': {{")
                    log(f"       'path': ['{path}']")
                    log(f"   }}")
                    break
        
    except Exception as e:
        log(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 