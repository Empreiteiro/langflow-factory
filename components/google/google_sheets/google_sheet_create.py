from lfx.custom import Component
from lfx.io import HandleInput, StrInput, FileInput, Output
from lfx.schema import Data
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import pandas as pd

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
        FileInput(
            name="credentials_file",
            display_name="Google Credentials File",
            file_types=["json"],
            required=True,
        ),
        StrInput(
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

    def create_sheet(self) -> Data:
        try:
            if not isinstance(self.credentials_file, str):
                raise ValueError("Expected credentials_file to be a file path string.")

            with open(self.credentials_file, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)

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
                # Convert DataFrame to list of dictionaries
                rows = raw_payload.to_dict('records')
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
            
            spreadsheet_body = {
                "properties": {
                    "title": self.sheet_name
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
            values_to_insert.extend([
                [item.get(col, "") for col in headers] for item in rows
            ])

            # Insert data into the sheet
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{tab_name}!A1",
                valueInputOption="RAW",
                body={"values": values_to_insert}
            ).execute()

            self.status = f"Created new sheet '{self.sheet_name}' with {len(rows)} data rows"
            return Data(data={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
                "sheet_name": self.sheet_name,
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
