from langflow.custom import Component
from langflow.io import HandleInput, StrInput, SecretStrInput, Output
from langflow.schema import Data
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import pandas as pd
from datetime import datetime, date

class AppendToGoogleSheet(Component):
    display_name = "Add Rows Google Sheet"
    description = "Appends JSON rows to the next available line in a Google Sheet."
    icon = "table"
    name = "Add Rows Google Sheet"

    inputs = [
        HandleInput(
            name="payload",
            display_name="Payload",
            info="A dictionary, list of dictionaries, DataFrame, or dictionary with a 'results' list to append to the sheet.",
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

    def append_data(self) -> Data:
        try:
            # Parse the JSON credentials from the secret key string
            try:
                credentials_dict = json.loads(self.service_account_key)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in service account key: {str(e)}"
                raise ValueError(msg) from e

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
                raise ValueError("No data to append to the sheet.")

            # Prepare data for appending with better error handling
            values_to_append = []
            for i, item in enumerate(rows):
                try:
                    cleaned_row = []
                    for col in headers:
                        raw_value = item.get(col, "")
                        cleaned_value = self._clean_value(raw_value)
                        cleaned_row.append(cleaned_value)
                    values_to_append.append(cleaned_row)
                except Exception as e:
                    self.log(f"Error processing row {i}: {str(e)}")
                    self.log(f"Problematic row data: {item}")
                    # Add a row with empty strings if there's an error
                    values_to_append.append(["" for _ in headers])

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
