from lfx.custom import Component
from lfx.io import DropdownInput, FileInput, MessageInput, Output, SecretStrInput, TabInput
from lfx.schema import Data
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io
import json


class GoogleDriveReader(Component):
    display_name = "Google Drive Reader"
    description = "Reads a file from Google Drive and returns its content."
    icon = "Google"
    name = "GoogleDriveReader"

    GOOGLE_MIME_EXPORTS = [
        ("Auto", "auto"),
        ("Plain Text", "text/plain"),
        ("PDF", "application/pdf"),
    ]

    inputs = [
        TabInput(
            name="auth_type",
            display_name="Authentication Type",
            options=["secret", "file"],
            value="secret",
            info="Select the authentication method for Google Cloud Platform credentials. 'secret' for Secret String, 'file' for JSON File.",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="service_account_key",
            display_name="GCP Credentials Secret Key",
            info="Your Google Cloud Platform service account JSON key as a secret string (complete JSON content).",
            required=True,
            advanced=True,
            show=True,
        ),
        FileInput(
            name="service_account_json",
            display_name="GCP Credentials JSON File",
            file_types=["json"],
            info="Upload your Google Cloud Platform service account JSON key.",
            required=True,
            advanced=True,
            show=False,
        ),
        MessageInput(
            name="file_id",
            display_name="File ID",
            info="Google Drive file ID to read.",
            required=True,
            tool_mode=True,
        ),
        DropdownInput(
            name="export_mime_type",
            display_name="Export As",
            info="Export Google Docs/Slides/Sheets to a specific format. Auto keeps original for binary files.",
            options=[value for _, value in GOOGLE_MIME_EXPORTS],
            value="auto",
        ),
    ]

    outputs = [
        Output(name="file_content", display_name="File Content", method="read_file"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update build configuration to show/hide fields based on authentication type selection."""
        if field_name != "auth_type":
            return build_config

        auth_type = str(field_value) if field_value else "secret"
        if auth_type not in ["secret", "file"]:
            auth_type = "secret"

        if "service_account_key" in build_config:
            build_config["service_account_key"]["show"] = False
        if "service_account_json" in build_config:
            build_config["service_account_json"]["show"] = False

        if auth_type == "secret":
            if "service_account_key" in build_config:
                build_config["service_account_key"]["show"] = True
        elif auth_type == "file":
            if "service_account_json" in build_config:
                build_config["service_account_json"]["show"] = True

        return build_config

    def _extract_message_text(self, value):
        if hasattr(value, "content"):
            return value.content
        if hasattr(value, "text"):
            return value.text
        if hasattr(value, "message"):
            return value.message
        return str(value)

    def _load_credentials(self):
        auth_type = getattr(self, "auth_type", "secret")
        auth_type = str(auth_type) if auth_type else "secret"
        if auth_type not in ["secret", "file"]:
            auth_type = "secret"

        if auth_type == "file":
            if not hasattr(self, "service_account_json") or not self.service_account_json:
                raise ValueError("Service account JSON file is required when using file authentication.")
            try:
                with open(self.service_account_json, "r", encoding="utf-8") as f:
                    credentials_dict = json.load(f)
            except FileNotFoundError:
                raise ValueError(f"Service account JSON file not found: {self.service_account_json}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service account file: {str(e)}")
        else:
            if not hasattr(self, "service_account_key") or not self.service_account_key:
                raise ValueError("Service account key is required when using secret string authentication.")
            try:
                credentials_dict = json.loads(self.service_account_key)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service account key: {str(e)}")

        return service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

    def _download_media(self, service, file_id):
        request = service.files().get_media(fileId=file_id)
        return self._execute_download(request)

    def _export_media(self, service, file_id, mime_type):
        request = service.files().export_media(fileId=file_id, mimeType=mime_type)
        return self._execute_download(request)

    def _execute_download(self, request):
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue()

    def read_file(self) -> Data:
        try:
            credentials = self._load_credentials()
            drive_service = build("drive", "v3", credentials=credentials)

            file_id = self._extract_message_text(self.file_id).strip()
            if not file_id:
                raise ValueError("File ID cannot be empty.")

            metadata = drive_service.files().get(
                fileId=file_id, fields="id,name,mimeType,modifiedTime,size"
            ).execute()

            mime_type = metadata.get("mimeType", "")
            export_mime_type = getattr(self, "export_mime_type", "auto") or "auto"

            if mime_type.startswith("application/vnd.google-apps"):
                if export_mime_type == "auto":
                    export_mime_type = "text/plain"
                file_bytes = self._export_media(drive_service, file_id, export_mime_type)
                output_mime_type = export_mime_type
            else:
                file_bytes = self._download_media(drive_service, file_id)
                output_mime_type = mime_type

            text_content = None
            try:
                text_content = file_bytes.decode("utf-8")
            except Exception:
                text_content = None

            return Data(
                data={
                    "file_id": metadata.get("id"),
                    "file_name": metadata.get("name"),
                    "mime_type": output_mime_type,
                    "modified_time": metadata.get("modifiedTime"),
                    "size": metadata.get("size"),
                    "text": text_content,
                    "bytes": file_bytes,
                }
            )
        except Exception as e:
            self.log(f"Error reading file: {e}")
            return Data(data={"error": str(e)})
