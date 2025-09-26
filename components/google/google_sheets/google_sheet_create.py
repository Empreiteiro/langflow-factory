from lfx.custom import Component
from lfx.io import HandleInput, StrInput, FileInput, Output, SecretStrInput, MessageInput
from lfx.schema import Data
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import pandas as pd
from datetime import datetime, date

class CreateGoogleSheet(Component):
    display_name = "Create Google Sheet"
    description = "Creates a new Google Sheet in the specified folder and populates it with JSON data or DataFrame."
    icon = "plus-square"
    name = "Create Google Sheet"

    inputs = [
        HandleInput(
            name="payload",
            display_name="Payload",
            info="A dictionary, list of dictionaries, DataFrame, or dictionary with a 'results' list to populate the sheet.",
            input_types=["Data", "DataFrame"],
            required=True
        ),
        SecretStrInput(
            name="service_account_key",
            display_name="GCP Credentials Secret Key",
            info="Your Google Cloud Platform service account JSON key as a secret string (complete JSON content).",
            required=True,
            advanced=True,
        ),
        MessageInput(
            name="sheet_name",
            display_name="Sheet Name",
            info="The name for the new sheet to be created.",
            required=True,
        ),
        StrInput(
            name="folder_id",
            display_name="Folder ID",
            info="The ID of the Google Drive folder where the sheet should be created (optional - if empty, creates in root).",
            required=False,
        ),
        StrInput(
            name="tab_name",
            display_name="Tab Name",
            info="The name for the first tab in the sheet (default: Sheet1).",
            required=False,
            value="Sheet1"
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="create_sheet")
    ]

    def _clean_value(self, value):
        """Clean and format values for Google Sheets compatibility."""
        if value is None or pd.isna(value):
            return ""
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, pd.Timestamp):
            return value.isoformat()
        elif isinstance(value, (int, float)):
            # Handle NaN values
            if pd.isna(value):
                return ""
            return value
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, (list, dict)):
            return json.dumps(value)
        else:
            # Convert to string and handle any special characters
            str_value = str(value)
            # Remove problematic characters that might cause JSON issues
            if ".638000+00:00" in str_value or "Timestamp" in str_value:
                # This looks like a pandas timestamp, try to parse it
                try:
                    if hasattr(value, 'isoformat'):
                        return value.isoformat()
                    else:
                        return pd.to_datetime(value).isoformat()
                except:
                    return str_value
            return str_value

    def create_sheet(self) -> Data:
        try:
            # Parse the JSON credentials from the secret key string
            try:
                credentials_dict = json.loads(self.service_account_key)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in service account key: {str(e)}"
                raise ValueError(msg) from e

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )

            sheets_service = build("sheets", "v4", credentials=credentials)
            drive_service = build("drive", "v3", credentials=credentials)

            # Extract raw content from Data wrapper if needed
            raw_payload = self.payload.data if isinstance(self.payload, Data) else self.payload

            # Handle DataFrame
            if isinstance(raw_payload, pd.DataFrame):
                # Convert DataFrame to list of dictionaries, handling all data types properly
                self.log(f"Processing DataFrame with shape: {raw_payload.shape}")
                self.log(f"DataFrame columns: {list(raw_payload.columns)}")
                self.log(f"DataFrame dtypes: {raw_payload.dtypes.to_dict()}")
                
                # Clean the DataFrame first - replace NaN values and convert problematic types
                cleaned_df = raw_payload.copy()
                
                # Convert any datetime columns to string format
                for col in cleaned_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
                        cleaned_df[col] = cleaned_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                        self.log(f"Converted datetime column '{col}' to string format")
                
                # Fill NaN values with empty strings
                cleaned_df = cleaned_df.fillna("")
                
                # Convert to list of dictionaries
                rows = cleaned_df.to_dict('records')
                self.log(f"Converted DataFrame to {len(rows)} rows")
            elif isinstance(raw_payload, str):
                try:
                    raw_payload = json.loads(raw_payload)
                except Exception as e:
                    raise ValueError(f"Payload string could not be parsed as JSON: {str(e)}")
                
                if isinstance(raw_payload, dict):
                    if "results" in raw_payload and isinstance(raw_payload["results"], list):
                        rows = raw_payload["results"]
                    else:
                        rows = [raw_payload]
                elif isinstance(raw_payload, list) and all(isinstance(r, dict) for r in raw_payload):
                    rows = raw_payload
                else:
                    raise ValueError(f"Payload string could not be recognized. Type: {type(raw_payload)}, value: {str(raw_payload)[:300]}")
            elif isinstance(raw_payload, dict):
                if "results" in raw_payload and isinstance(raw_payload["results"], list):
                    rows = raw_payload["results"]
                else:
                    rows = [raw_payload]
            elif isinstance(raw_payload, list) and all(isinstance(r, dict) for r in raw_payload):
                rows = raw_payload
            else:
                raise ValueError(f"Payload could not be recognized. Type: {type(raw_payload)}, value: {str(raw_payload)[:300]}. Supported types: DataFrame, dict, list of dicts, or JSON string.")

            if not rows:
                raise ValueError("No data to populate the sheet with.")

            # Generate headers from the first row
            headers = list(rows[0].keys())

            # Create the spreadsheet
            tab_name = self.tab_name if self.tab_name else "Sheet1"
            
            # Extract text from MessageInput
            sheet_name_text = self.sheet_name.text if hasattr(self.sheet_name, 'text') else str(self.sheet_name)
            
            spreadsheet_body = {
                "properties": {
                    "title": sheet_name_text
                },
                "sheets": [
                    {
                        "properties": {
                            "title": tab_name
                        }
                    }
                ]
            }

            spreadsheet = sheets_service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            spreadsheet_id = spreadsheet.get("spreadsheetId")
            spreadsheet_url = spreadsheet.get("spreadsheetUrl")

            # Move to specified folder if folder_id is provided
            if self.folder_id:
                # Remove from root and add to specified folder
                file_metadata = drive_service.files().get(
                    fileId=spreadsheet_id,
                    fields="parents"
                ).execute()
                
                previous_parents = ",".join(file_metadata.get("parents"))
                
                drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=self.folder_id,
                    removeParents=previous_parents,
                    fields="id, parents"
                ).execute()

            # Prepare data for insertion
            values_to_insert = [headers]  # Start with headers
            
            # Process each row with better error handling
            for i, row in enumerate(rows):
                try:
                    cleaned_row = []
                    for col in headers:
                        raw_value = row.get(col, "")
                        cleaned_value = self._clean_value(raw_value)
                        cleaned_row.append(cleaned_value)
                    values_to_insert.append(cleaned_row)
                except Exception as e:
                    self.log(f"Error processing row {i}: {str(e)}")
                    self.log(f"Problematic row data: {row}")
                    # Add a row with empty strings if there's an error
                    values_to_insert.append(["" for _ in headers])
            
            self.log(f"Prepared {len(values_to_insert)} rows for insertion (including header)")

            # Insert data into the sheet
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{tab_name}!A1",
                valueInputOption="RAW",
                body={"values": values_to_insert}
            ).execute()

            self.status = f"Created new sheet '{sheet_name_text}' with {len(rows)} data rows"
            return Data(data={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
                "sheet_name": sheet_name_text,
                "tab_name": tab_name,
                "rows_inserted": len(rows),
                "headers": headers,
                "folder_id": self.folder_id if self.folder_id else "root"
            })

        except Exception as e:
            error_msg = f"Error creating sheet: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"status": "error", "message": error_msg})
