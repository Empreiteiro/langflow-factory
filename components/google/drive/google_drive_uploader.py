from langflow.custom import Component
from langflow.io import StrInput, FileInput, MultilineInput, DropdownInput, Output, MessageInput
from langflow.schema import Data
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import os
import base64
import json
import time
import re

class GoogleDriveUploader(Component):
    display_name = "Google Drive Uploader"
    description = "Uploads a file to a specified Google Drive folder or creates a Google Slides presentation or Google Docs document."
    icon = "Google"
    name = "GoogleDriveUploader"

    FILE_TYPE_CHOICES = ["jpg", "txt", "json", "mp3", "slides", "docs"]

    inputs = [
        MultilineInput(
            name="file_content",
            display_name="File Content",
            info="The content of the file to be saved and uploaded, or the text for the first slide/document.",
            required=True,
            tool_mode=True,
        ),
        MessageInput(
            name="file_name",
            display_name="File Name",
            info="The name of the file to be saved (without extension), or the presentation/document title. Minimum 3 characters.",
            required=True,
            tool_mode=True,
        ),
        DropdownInput(
            name="file_type",
            display_name="File Type",
            options=FILE_TYPE_CHOICES,
            info="Select the type of the file.",
            required=True,
        ),
        MessageInput(
            name="folder_id",
            display_name="Destination Folder ID",
            info="The Google Drive folder ID where the file will be uploaded. The folder must be shared with the service account email.",
            required=True,
            tool_mode=True,
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
        Output(name="file_url", display_name="File URL", method="upload_file"),
    ]

    def _sanitize_filename(self, filename):
        """Sanitize filename to ensure it's valid and has minimum length"""
        # Handle Message object from MessageInput
        if hasattr(filename, 'content'):
            filename = filename.content
        elif hasattr(filename, 'text'):
            filename = filename.text
        elif hasattr(filename, 'message'):
            filename = filename.message
        else:
            filename = str(filename)
        
        if not filename or len(filename.strip()) < 3:
            raise ValueError("File name must be at least 3 characters long")
        
        # Remove invalid characters and replace with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename.strip())
        
        # Ensure it doesn't start with a dot or space
        sanitized = sanitized.lstrip('. ')
        
        if not sanitized:
            raise ValueError("File name cannot be empty after sanitization")
        
        return sanitized

    def _extract_folder_id(self, folder_id):
        """Extract folder ID from MessageInput object"""
        # Handle Message object from MessageInput
        if hasattr(folder_id, 'content'):
            folder_id = folder_id.content
        elif hasattr(folder_id, 'text'):
            folder_id = folder_id.text
        elif hasattr(folder_id, 'message'):
            folder_id = folder_id.message
        else:
            folder_id = str(folder_id)
        
        # Remove any whitespace and validate
        folder_id = folder_id.strip()
        if not folder_id:
            raise ValueError("Folder ID cannot be empty")
        
        return folder_id

    def upload_file(self) -> Data:
        try:
            # Validate and sanitize filename
            sanitized_filename = self._sanitize_filename(self.file_name)
            
            # Extract folder ID from MessageInput
            extracted_folder_id = self._extract_folder_id(self.folder_id)
            
            with open(self.service_account_json, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/presentations",
                    "https://www.googleapis.com/auth/documents"
                ]
            )
            drive_service = build("drive", "v3", credentials=credentials)

            if self.file_type == "slides":
                slides_service = build("slides", "v1", credentials=credentials)

                file_metadata = {
                    "name": sanitized_filename,
                    "mimeType": "application/vnd.google-apps.presentation",
                    "parents": [extracted_folder_id],
                }

                created_file = drive_service.files().create(body=file_metadata, fields="id").execute()
                presentation_id = created_file["id"]

                # Espera brevemente para garantir que o arquivo esteja disponível
                time.sleep(2)

                presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
                slide_id = presentation["slides"][0]["objectId"]

                text_box_id = "TextBox_01"
                requests = [
                    {
                        "createShape": {
                            "objectId": text_box_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "height": {"magnitude": 3000000, "unit": "EMU"},
                                    "width": {"magnitude": 6000000, "unit": "EMU"}
                                },
                                "transform": {
                                    "scaleX": 1,
                                    "scaleY": 1,
                                    "translateX": 1000000,
                                    "translateY": 1000000,
                                    "unit": "EMU"
                                }
                            }
                        }
                    },
                    {
                        "insertText": {
                            "objectId": text_box_id,
                            "insertionIndex": 0,
                            "text": self.file_content
                        }
                    }
                ]

                slides_service.presentations().batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                ).execute()

                file_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
                return Data(data={"file_url": file_url})

            elif self.file_type == "docs":
                docs_service = build("docs", "v1", credentials=credentials)

                file_metadata = {
                    "name": sanitized_filename,
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [extracted_folder_id],
                }

                created_file = drive_service.files().create(body=file_metadata, fields="id").execute()
                document_id = created_file["id"]

                # Espera brevemente para garantir que o arquivo esteja disponível
                time.sleep(2)

                # Insert text into the document
                requests = [
                    {
                        "insertText": {
                            "location": {
                                "index": 1
                            },
                            "text": self.file_content
                        }
                    }
                ]

                docs_service.documents().batchUpdate(
                    documentId=document_id, body={"requests": requests}
                ).execute()

                file_url = f"https://docs.google.com/document/d/{document_id}/edit"
                return Data(data={"file_url": file_url})

            # Handle other file types
            file_path = sanitized_filename
            mime_type = ""

            if self.file_type == "jpg":
                file_path += ".jpg"
                mime_type = "image/jpeg"
                file_data = base64.b64decode(self.file_content)
            elif self.file_type == "txt":
                file_path += ".txt"
                mime_type = "text/plain"
                file_data = self.file_content.encode("utf-8")
            elif self.file_type == "json":
                file_path += ".json"
                mime_type = "application/json"
                file_data = json.dumps(json.loads(self.file_content), indent=4).encode("utf-8")
            elif self.file_type == "mp3":
                file_path += ".mp3"
                mime_type = "audio/mpeg"
                file_data = self.file_content
                if isinstance(file_data, str):
                    # Se for string, assume que é base64
                    try:
                        file_data = base64.b64decode(file_data)
                    except Exception as e:
                        raise ValueError(f"Invalid base64 data for MP3: {str(e)}")
                elif not isinstance(file_data, bytes):
                    raise ValueError("Audio data must be passed as base64 string or bytes.")
            else:
                raise ValueError("Unsupported file type.")

            with open(file_path, "wb") as file:
                file.write(file_data)

            file_metadata = {"name": os.path.basename(file_path), "parents": [extracted_folder_id]}
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            file_id = uploaded_file.get("id")
            file_url = f"https://drive.google.com/file/d/{file_id}/view"

            os.remove(file_path)
            return Data(data={"file_url": file_url})

        except Exception as e:
            self.log(f"Error uploading file: {e}")
            return Data(data={"error": str(e)})
