from langflow.custom import Component
from langflow.io import StrInput, FileInput, MessageInput, Output, HandleInput
from langflow.schema import Data, Message
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import re

class GoogleDriveFolderCreator(Component):
    display_name = "Google Drive Folder Creator"
    description = "Creates a new folder in a specified Google Drive location."
    icon = "Google"
    name = "GoogleDriveFolderCreator"

    inputs = [
        HandleInput(
            name="trigger",
            display_name="Trigger",
            input_types=["Message","Text","Data"],
            value="google_news_url",
            advanced=True,
        ),
        MessageInput(
            name="folder_name",
            display_name="Folder Name",
            info="The name of the folder to be created. Minimum 3 characters.",
            required=True,
            tool_mode=True,
        ),
        StrInput(
            name="parent_folder_id",
            display_name="Parent Folder ID",
            info="The Google Drive folder ID where the new folder will be created. The folder must be shared with the service account email.",
            required=True,
        ),
        FileInput(
            name="service_account_json",
            display_name="GCP Credentials JSON File",
            file_types=["json"],
            info="Upload your Google Cloud Platform service account JSON key.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="folder_result", display_name="Response", method="create_folder"),
    ]

    def _sanitize_folder_name(self, folder_name):
        """Sanitize folder name to ensure it's valid and has minimum length"""
        # Handle Message object from MessageInput
        if hasattr(folder_name, 'content'):
            folder_name = folder_name.content
        elif hasattr(folder_name, 'text'):
            folder_name = folder_name.text
        elif hasattr(folder_name, 'message'):
            folder_name = folder_name.message
        else:
            folder_name = str(folder_name)
        
        if not folder_name or len(folder_name.strip()) < 3:
            raise ValueError("Folder name must be at least 3 characters long")
        
        # Remove invalid characters and replace with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', folder_name.strip())
        
        # Ensure it doesn't start with a dot or space
        sanitized = sanitized.lstrip('. ')
        
        if not sanitized:
            raise ValueError("Folder name cannot be empty after sanitization")
        
        return sanitized

    def create_folder(self) -> Message:
        try:
            # Validate and sanitize folder name
            sanitized_folder_name = self._sanitize_folder_name(self.folder_name)
            
            with open(self.service_account_json, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            drive_service = build("drive", "v3", credentials=credentials)

            # Create folder metadata
            folder_metadata = {
                "name": sanitized_folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.parent_folder_id],
            }

            # Create the folder
            created_folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = created_folder.get("id")

            # Return only the folder ID
            return Message(text=folder_id)

        except Exception as e:
            error_message = f"Error creating folder: {e}"
            self.log(error_message)
            return Message(text=error_message)
