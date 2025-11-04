from langflow.custom import Component
from langflow.io import StrInput, FileInput, MultilineInput, DropdownInput, Output, MessageInput, HandleInput, SecretStrInput, TabInput
from langflow.schema import Data, DataFrame, Message
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
    description = "Uploads a file to a specified Google Drive folder."
    icon = "Google"
    name = "GoogleDriveUploader"

    FILE_TYPE_CHOICES = ["txt", "json", "csv", "xlsx", "slides", "docs", "jpg", "mp3", "pdf"]

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
        HandleInput(
            name="input",
            display_name="File Content",
            info="The input to save.",
            dynamic=True,
            input_types=["Data", "DataFrame", "Message"],
            required=True,
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
            display_name="File Format",
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

    ]

    outputs = [
        Output(name="file_url", display_name="File URL", method="upload_file"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update build configuration to show/hide fields based on authentication type selection."""
        if field_name != "auth_type":
            return build_config

        # Extract selected authentication type from TabInput (should be a string)
        auth_type = str(field_value) if field_value else "secret"

        # Normalize auth_type value
        if auth_type not in ["secret", "file"]:
            auth_type = "secret"  # Default to secret

        # Hide both authentication fields first
        if "service_account_key" in build_config:
            build_config["service_account_key"]["show"] = False
        if "service_account_json" in build_config:
            build_config["service_account_json"]["show"] = False

        # Show the appropriate field based on selection
        if auth_type == "secret":
            if "service_account_key" in build_config:
                build_config["service_account_key"]["show"] = True
        elif auth_type == "file":
            if "service_account_json" in build_config:
                build_config["service_account_json"]["show"] = True

        return build_config

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

    def _extract_content_from_input(self, input_data):
        """Extract content from different input types (Data, DataFrame, Message)"""
        try:
            if isinstance(input_data, Message):
                return input_data.text or str(input_data)
            
            elif isinstance(input_data, DataFrame):
                # Convert DataFrame to CSV string
                if hasattr(input_data, 'to_csv'):
                    return input_data.to_csv(index=False)
                else:
                    return str(input_data)
            
            elif isinstance(input_data, Data):
                # Try to extract content from Data object
                if hasattr(input_data, 'data') and input_data.data:
                    data_content = input_data.data
                    
                    # If data is a dictionary, try common content keys
                    if isinstance(data_content, dict):
                        for key in ['content', 'text', 'message', 'body', 'value', 'result']:
                            if key in data_content and data_content[key]:
                                return str(data_content[key])
                        
                        # If no common keys, try to serialize as JSON
                        try:
                            return json.dumps(data_content, indent=2, ensure_ascii=False)
                        except Exception:
                            return str(data_content)
                    
                    # If data is not a dict, convert to string
                    return str(data_content)
                
                # Fallback to string representation
                return str(input_data)
            
            # For any other type, convert to string
            return str(input_data)
            
        except Exception as e:
            self.log(f"Error extracting content from input: {str(e)}")
            return str(input_data)

    def _determine_file_type_from_content(self, content, file_type):
        """Determine the best file type based on content and user selection"""
        if file_type in ["slides", "docs", "jpg", "mp3", "pdf"]:
            return file_type
        
        # Auto-detect based on input type if user selected csv/xlsx/json
        if isinstance(self.input, DataFrame):
            if file_type in ["csv", "xlsx", "pdf"]:
                return file_type
            return "csv"  # Default for DataFrame
        
        # For Data inputs, try to detect format
        if isinstance(self.input, Data):
            if file_type == "json":
                try:
                    json.loads(content)
                    return "json"
                except:
                    pass
            elif file_type == "csv":
                # Check if content looks like CSV
                if ',' in content and '\n' in content:
                    return "csv"
        
        # For Message inputs, default to txt unless specifically requested
        if isinstance(self.input, Message):
            if file_type in ["txt", "json", "csv", "pdf"]:
                return file_type
            return "txt"
        
        # Fallback to user selection or txt
        return file_type if file_type in self.FILE_TYPE_CHOICES else "txt"

    def upload_file(self) -> Data:
        try:
            # Extract content from input
            file_content = self._extract_content_from_input(self.input)
            
            # Validate and sanitize filename
            sanitized_filename = self._sanitize_filename(self.file_name)
            
            # Extract folder ID from MessageInput
            extracted_folder_id = self._extract_folder_id(self.folder_id)
            
            # Determine the actual file type to use
            actual_file_type = self._determine_file_type_from_content(file_content, self.file_type)
            
            # Parse credentials based on authentication type
            auth_type = getattr(self, "auth_type", "secret")
            
            # Extract auth_type value from TabInput (should be a string)
            auth_type = str(auth_type) if auth_type else "secret"
            
            # Normalize to "secret" or "file"
            if auth_type not in ["secret", "file"]:
                auth_type = "secret"  # Default to secret
            
            if auth_type == "file":
                # Load credentials from JSON file
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
                # Parse the JSON credentials from the secret key string (default)
                if not hasattr(self, "service_account_key") or not self.service_account_key:
                    raise ValueError("Service account key is required when using secret string authentication.")
                try:
                    credentials_dict = json.loads(self.service_account_key)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in service account key: {str(e)}")

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/presentations",
                    "https://www.googleapis.com/auth/documents"
                ]
            )
            drive_service = build("drive", "v3", credentials=credentials)

            if actual_file_type == "slides":
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
                            "text": file_content
                        }
                    }
                ]

                slides_service.presentations().batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                ).execute()

                file_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
                return Data(data={"file_url": file_url})

            elif actual_file_type == "docs":
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
                            "text": file_content
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

            if actual_file_type == "jpg":
                file_path += ".jpg"
                mime_type = "image/jpeg"
                try:
                    file_data = base64.b64decode(file_content)
                except Exception as e:
                    raise ValueError(f"Invalid base64 data for JPG: {str(e)}")
            elif actual_file_type == "txt":
                file_path += ".txt"
                mime_type = "text/plain"
                file_data = file_content.encode("utf-8")
            elif actual_file_type == "json":
                file_path += ".json"
                mime_type = "application/json"
                # Try to parse and format JSON, fallback to original content
                try:
                    parsed_json = json.loads(file_content)
                    formatted_json = json.dumps(parsed_json, indent=4, ensure_ascii=False)
                    file_data = formatted_json.encode("utf-8")
                except json.JSONDecodeError:
                    # If not valid JSON, save as-is
                    file_data = file_content.encode("utf-8")
            elif actual_file_type == "csv":
                file_path += ".csv"
                mime_type = "text/csv"
                file_data = file_content.encode("utf-8")
            elif actual_file_type == "xlsx":
                file_path += ".xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                # For XLSX, we need to convert the content to Excel format
                try:
                    import pandas as pd
                    from io import StringIO
                    
                    # Try to parse as CSV first
                    try:
                        df = pd.read_csv(StringIO(file_content))
                    except:
                        # If not CSV, try to create DataFrame from the content
                        if isinstance(self.input, DataFrame):
                            df = self.input
                        else:
                            # Create a simple DataFrame with the content
                            df = pd.DataFrame({'content': [file_content]})
                    
                    # Save as Excel
                    temp_excel_path = file_path + "_temp"
                    df.to_excel(temp_excel_path, index=False)
                    
                    with open(temp_excel_path, 'rb') as f:
                        file_data = f.read()
                    
                    os.remove(temp_excel_path)
                    
                except ImportError:
                    # If pandas not available, fallback to CSV
                    self.log("pandas not available, saving as CSV instead of XLSX")
                    file_path = sanitized_filename + ".csv"
                    mime_type = "text/csv"
                    file_data = file_content.encode("utf-8")
                except Exception as e:
                    self.log(f"Error creating XLSX: {str(e)}, falling back to CSV")
                    file_path = sanitized_filename + ".csv"
                    mime_type = "text/csv"
                    file_data = file_content.encode("utf-8")
            elif actual_file_type == "mp3":
                file_path += ".mp3"
                mime_type = "audio/mpeg"
                if isinstance(file_content, str):
                    # Se for string, assume que é base64
                    try:
                        file_data = base64.b64decode(file_content)
                    except Exception as e:
                        raise ValueError(f"Invalid base64 data for MP3: {str(e)}")
                elif isinstance(file_content, bytes):
                    file_data = file_content
                else:
                    raise ValueError("Audio data must be passed as base64 string or bytes.")
            elif actual_file_type == "pdf":
                file_path += ".pdf"
                mime_type = "application/pdf"
                # Generate PDF using reportlab
                temp_pdf_path = file_path + "_temp"
                self._create_pdf_from_content(file_content, temp_pdf_path)
                
                with open(temp_pdf_path, 'rb') as f:
                    file_data = f.read()
                
                os.remove(temp_pdf_path)
            else:
                # Default to txt for unsupported types
                file_path += ".txt"
                mime_type = "text/plain"
                file_data = file_content.encode("utf-8")

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

    def _create_pdf_from_content(self, content: str, pdf_path: str) -> None:
        """Create a PDF file from content using reportlab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError as e:
            raise ImportError("reportlab is not installed. Please install it using `uv pip install reportlab`.") from e

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Try to create a table if input is DataFrame
        if isinstance(self.input, DataFrame):
            self._create_dataframe_pdf(self.input, elements)
        # Try to create a table if input is Data with tabular data
        elif isinstance(self.input, Data):
            try:
                import pandas as pd
                df = pd.DataFrame(self.input.data) if hasattr(self.input, "data") and self.input.data else None
                if df is not None and not df.empty:
                    self._create_dataframe_pdf(df, elements)
                else:
                    # Save as formatted text
                    self._create_text_pdf(content, elements, styles)
            except Exception:
                # Save as formatted text if conversion fails
                self._create_text_pdf(content, elements, styles)
        else:
            # Save as formatted text for Message or other types
            self._create_text_pdf(content, elements, styles)

        doc.build(elements)

    def _create_dataframe_pdf(self, dataframe, elements):
        """Create a PDF table from a DataFrame."""
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle

        # Convert DataFrame to list of lists for table
        if hasattr(dataframe, 'columns') and hasattr(dataframe, 'values'):
            data = [dataframe.columns.tolist()] + dataframe.values.tolist()
        else:
            # Try to convert to pandas DataFrame
            import pandas as pd
            if isinstance(dataframe, pd.DataFrame):
                data = [dataframe.columns.tolist()] + dataframe.values.tolist()
            else:
                raise ValueError("Cannot convert input to DataFrame for PDF table")

        # Create table
        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]
            )
        )

        elements.append(table)

    def _create_text_pdf(self, content: str, elements, styles):
        """Create a PDF with formatted text content."""
        from reportlab.platypus import Paragraph

        # Use the content passed as parameter (already extracted from input)
        # Escape HTML and convert newlines
        text_escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        para = Paragraph(text_escaped, styles["Normal"])
        elements.append(para)
