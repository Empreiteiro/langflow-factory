from lfx.custom import Component
from lfx.io import DropdownInput, FileInput, MessageInput, Output, SecretStrInput, TabInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io
import json


class GoogleDriveFolderReader(Component):
    display_name = "Google Drive Folder Reader"
    description = "Reads all documents from a Google Drive folder."
    icon = "Google"
    name = "GoogleDriveFolderReader"

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
            name="folder_id",
            display_name="Folder ID",
            info="Google Drive folder ID to read documents from.",
            required=True,
            tool_mode=True,
        ),
        DropdownInput(
            name="export_mime_type",
            display_name="Export As",
            info="Export Google Docs/Slides/Sheets to a specific format.",
            options=["text/plain", "application/pdf"],
            value="text/plain",
        ),
        DropdownInput(
            name="include_non_google_docs",
            display_name="Include Non-Google Docs",
            info="When true, download non-Google files too.",
            options=["false", "true"],
            value="false",
        ),
    ]

    outputs = [
        Output(name="documents", display_name="Documents", method="read_folder"),
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

    def _execute_download(self, request):
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue()

    def _fetch_file_content(self, service, file_id, mime_type, export_mime_type):
        if mime_type.startswith("application/vnd.google-apps"):
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            output_mime_type = export_mime_type
        else:
            request = service.files().get_media(fileId=file_id)
            output_mime_type = mime_type

        file_bytes = self._execute_download(request)
        try:
            text_content = file_bytes.decode("utf-8")
        except Exception:
            text_content = None
        return file_bytes, text_content, output_mime_type

    def read_folder(self) -> DataFrame:
        try:
            credentials = self._load_credentials()
            drive_service = build("drive", "v3", credentials=credentials)

            folder_id = self._extract_message_text(self.folder_id).strip()
            if not folder_id:
                raise ValueError("Folder ID cannot be empty.")

            include_non_google_docs = str(getattr(self, "include_non_google_docs", "false")).lower() == "true"
            export_mime_type = getattr(self, "export_mime_type", "text/plain") or "text/plain"

            query = f"'{folder_id}' in parents and trashed = false"
            page_token = None
            files = []

            while True:
                response = (
                    drive_service.files()
                    .list(
                        q=query,
                        fields="nextPageToken, files(id,name,mimeType,modifiedTime,size)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            documents = []
            for item in files:
                mime_type = item.get("mimeType", "")
                if not include_non_google_docs and not mime_type.startswith("application/vnd.google-apps"):
                    continue

                file_bytes, text_content, output_mime_type = self._fetch_file_content(
                    drive_service,
                    item.get("id"),
                    mime_type,
                    export_mime_type,
                )
                documents.append(
                    {
                        "folder_id": folder_id,
                        "document_count": 0,  # filled after list complete
                        "file_id": item.get("id"),
                        "file_name": item.get("name"),
                        "mime_type": output_mime_type,
                        "modified_time": item.get("modifiedTime"),
                        "size": item.get("size"),
                        "text": text_content,
                        "bytes": file_bytes,
                    }
                )

            total_documents = len(documents)
            for doc in documents:
                doc["document_count"] = total_documents

            data_rows = [Data(data=doc) for doc in documents]
            return DataFrame(data_rows)
        except Exception as e:
            self.log(f"Error reading folder: {e}")
            return DataFrame([Data(data={"error": str(e)})])
