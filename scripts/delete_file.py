import requests
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

def delete_file_v2(file_id, api_key, langflow_url):
    """
    Delete a specific file by its ID using the v2 files API.
    
    Args:
        file_id (str): File ID to delete
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
    
    Returns:
        dict: Response from the API
    """
    
    # API endpoint for v2 file deletion
    delete_url = f"{langflow_url}/api/v2/files/{file_id}"
    
    # Headers required for v2 API
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    try:
        # Send DELETE request to delete file
        response = requests.delete(delete_url, headers=headers)
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Return the response JSON
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error deleting file: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        raise

def delete_all_files_v2(api_key, langflow_url):
    """
    Delete all files associated with your user account using the v2 files API.
    
    Args:
        api_key (str): Langflow API key
        langflow_url (str): Langflow server URL
    
    Returns:
        dict: Response from the API
    """
    
    # API endpoint for v2 bulk file deletion
    delete_url = f"{langflow_url}/api/v2/files"
    
    # Headers required for v2 API
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    try:
        # Send DELETE request to delete all files
        response = requests.delete(delete_url, headers=headers)
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Return the response JSON
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error deleting all files: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        raise

def log(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def main():
    """Main function to handle command line arguments and execute file deletion."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Delete files from Langflow")
    parser.add_argument(
        "--file-id",
        help="File ID to delete (if not provided, will delete all files)"
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
        "--force",
        action="store_true",
        help="Skip confirmation prompt when deleting all files"
    )
    
    args = parser.parse_args()
    
    # Check if API key is available
    if not args.langflow_token:
        log("❌ Error: LANGFLOW_TOKEN environment variable not set.")
        log("Please set your API key in the .env file or use --langflow-token parameter")
        return
    
    try:
        if args.file_id:
            # Delete specific file
            log(f"🗑️  Deleting file with ID: {args.file_id}")
            result = delete_file_v2(args.file_id, args.langflow_token, args.langflow_url)
            
            log("✅ File deleted successfully!")
            log(f"📝 Message: {result.get('message', 'N/A')}")
            
        else:
            # Delete all files - require confirmation unless --force is used
            if not args.force:
                log("⚠️  WARNING: You are about to delete ALL files from your account!")
                confirmation = input("Type 'yes' to confirm: ")
                if confirmation.lower() != 'yes':
                    log("❌ Deletion cancelled.")
                    return
            
            log("🗑️  Deleting all files from your account...")
            result = delete_all_files_v2(args.langflow_token, args.langflow_url)
            
            log("✅ All files deleted successfully!")
            log(f"📝 Message: {result.get('message', 'N/A')}")
        
    except FileNotFoundError as e:
        log(f"❌ {e}")
    except ValueError as e:
        log(f"❌ {e}")
    except Exception as e:
        log(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()

