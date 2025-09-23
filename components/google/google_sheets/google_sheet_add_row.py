from lfx.custom import Component
from lfx.io import DataInput, StrInput, FileInput, Output
from lfx.schema import Data
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

class AppendToGoogleSheet(Component):
    display_name = "Add Rows Google Sheet"
    description = "Appends JSON rows to the next available line in a Google Sheet."
    icon = "table"
    name = "Add Rows Google Sheet"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="A dictionary, list of dictionaries, or dictionary with a 'results' list.",
            required=True
        ),
        FileInput(
            name="credentials_file",
            display_name="Google Credentials File",
            file_types=["json"],
            required=True,
        ),
        StrInput(
            name="spreadsheet_id",
            display_name="Spreadsheet ID",
            info="The ID of the spreadsheet (from the URL).",
            required=True,
        ),
        StrInput(
            name="sheet_name",
            display_name="Sheet Name",
            info="The tab name where data should be appended.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="append_data")
    ]

    def append_data(self) -> Data:
        try:
            if not isinstance(self.credentials_file, str):
                raise ValueError("Expected credentials_file to be a file path string.")

            with open(self.credentials_file, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )

            service = build("sheets", "v4", credentials=credentials)
            sheet = service.spreadsheets()

            metadata = sheet.get(spreadsheetId=self.spreadsheet_id).execute()
            sheet_titles = [s["properties"]["title"] for s in metadata.get("sheets", [])]
            if self.sheet_name not in sheet_titles:
                raise ValueError(f"Sheet '{self.sheet_name}' not found. Available: {sheet_titles}")

            header_range = f"{self.sheet_name}!1:1"
            header_result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=header_range
            ).execute()
            headers = header_result.get("values", [[]])[0]

            if not headers:
                raise ValueError("Sheet must have headers in the first row.")

            row_check_range = f"{self.sheet_name}!A:A"
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=row_check_range
            ).execute()
            current_rows = result.get("values", [])
            next_row_index = len(current_rows) + 1

            # Extract raw content from Data wrapper if needed
            raw_payload = self.payload.data if isinstance(self.payload, Data) else self.payload

            if isinstance(raw_payload, str):
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
                raise ValueError(f"Payload could not be recognized. Type: {type(raw_payload)}, value: {str(raw_payload)[:300]}")

            values_to_append = [
                [item.get(col, "") for col in headers] for item in rows
            ]

            sheet.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=self.sheet_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": values_to_append}
            ).execute()

            self.status = f"Appended {len(values_to_append)} rows"
            return Data(data={
                "status": "success",
                "rows_appended": len(values_to_append),
                "next_row_start": next_row_index,
                "headers": headers
            })

        except Exception as e:
            error_msg = f"Error appending data: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"status": "error", "message": error_msg})
