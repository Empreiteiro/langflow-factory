import requests
import os
import sys
import argparse
import mimetypes
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional


def upload_file_return_path_and_name(file_path: str, api_key: str, langflow_url: str) -> dict:
    """
    Upload a file to Langflow (v2 files API) and return only the path and name.

    Args:
        file_path: Local path to the file to upload.
        api_key: Langflow API key.
        langflow_url: Langflow base URL (e.g., http://localhost:3000).

    Returns:
        Dict with keys: { 'path': str, 'name': str }
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type = get_mime_type(file_extension) or "application/octet-stream"

    upload_url = f"{langflow_url}/api/v2/files"

    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
    }

    with open(file_path, "rb") as file_handle:
        files = {
            "file": (os.path.basename(file_path), file_handle, mime_type)
        }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()
            response_json = response.json()

            # Ensure required keys exist
            if "path" not in response_json or "name" not in response_json:
                raise ValueError("Response missing required keys 'path' or 'name'.")

            name_no_ext = os.path.splitext(response_json["name"])[0]
            return {
                "path": response_json["path"],
                "name": name_no_ext,
            }

        except requests.exceptions.RequestException as request_error:
            print(f"Error uploading file: {request_error}")
            if hasattr(request_error, "response") and request_error.response is not None:
                print(f"Response status: {request_error.response.status_code}")
                print(f"Response text: {request_error.response.text}")
            raise


def get_mime_type(file_extension: str) -> Optional[str]:
    """
    Return MIME type for a given file extension.
    """

    mime_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".zip": "application/zip",
        ".rar": "application/vnd.rar",
        ".7z": "application/x-7z-compressed",
        ".tar": "application/x-tar",
        ".gz": "application/gzip",
        ".bz2": "application/x-bzip2",
    }

    if file_extension in mime_types:
        return mime_types[file_extension]

    mime_type, _ = mimetypes.guess_type(f"file{file_extension}")
    return mime_type


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Upload file to Langflow and print only path and name"
    )
    parser.add_argument("file_path", help="Path to the file to upload")
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_URL", "http://localhost:3000"),
        help="Langflow URL (default: env LANGFLOW_URL or http://localhost:3000)",
    )
    parser.add_argument(
        "--langflow-token",
        default=os.getenv("LANGFLOW_TOKEN"),
        help="Langflow API token (default: env LANGFLOW_TOKEN)",
    )

    args = parser.parse_args()

    if not args.langflow_token:
        log("Error: LANGFLOW_TOKEN environment variable not set.")
        sys.exit(1)

    try:
        result = upload_file_return_path_and_name(
            file_path=args.file_path,
            api_key=args.langflow_token,
            langflow_url=args.langflow_url,
        )

        # Print only the requested results
        print(f"path: {result['path']}")
        print(f"name: {result['name']}")

    except FileNotFoundError as file_error:
        log(f"{file_error}")
        sys.exit(1)
    except ValueError as value_error:
        log(f"{value_error}")
        sys.exit(1)
    except Exception as generic_error:
        log(f"Unexpected error: {generic_error}")
        sys.exit(1)


if __name__ == "__main__":
    main()


