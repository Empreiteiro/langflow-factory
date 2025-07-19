from langflow.custom import Component
from langflow.io import StrInput, FileInput, Output, DataInput
from langflow.schema import DataFrame, Data
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

class GoogleSheetsQuery(Component):
    display_name = "Google Sheets Query"
    description = "Lists records from a Google Sheets spreadsheet and allows filtering. Can be triggered by webhook."
    icon = "table"
    name = "GoogleSheetsQuery"

    inputs = [
        DataInput(
            name="webhook_data",
            display_name="Webhook Trigger",
            info="Optional data from webhook trigger. Can override other inputs.",
            required=False,
            advanced=True
        ),
        FileInput(
            name="gcp_credentials_json",
            display_name="GCP Credentials JSON File",
            file_types=["json"],
            info="Upload your Google Cloud Platform service account JSON key.",
            required=True
        ),
        StrInput(
            name="spreadsheet_id",
            display_name="Spreadsheet ID",
            info="The ID of the Google Sheets spreadsheet.",
            required=True
        ),
        StrInput(
            name="range_name",
            display_name="Sheet Range",
            info="Example: 'Sheet1!A1:D100'.",
            required=True
        ),
        StrInput(
            name="query",
            display_name="Filter Query",
            info="Expression to filter results. Example: 'column1 == \"value\"'.",
            required=False
        )
    ]

    outputs = [
        Output(
            name="dataframe",
            display_name="DataFrame",
            method="build"
        )
    ]

    def build(self) -> DataFrame:
        try:
            spreadsheet_id = self.spreadsheet_id
            range_name = self.range_name
            query = self.query

            # Check if webhook_data provides overrides
            if isinstance(self.webhook_data, Data) and isinstance(self.webhook_data.data, dict):
                data = self.webhook_data.data
                spreadsheet_id = data.get("spreadsheet_id", spreadsheet_id)
                range_name = data.get("range_name", range_name)
                query = data.get("query", query)

            if not self.gcp_credentials_json:
                raise ValueError("GCP credentials file is empty.")

            with open(self.gcp_credentials_json, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )

            service = build("sheets", "v4", credentials=credentials)
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get("values", [])

            if not values:
                return DataFrame(pd.DataFrame())

            df = pd.DataFrame(values[1:], columns=values[0])

            if query:
                df = df.query(query, engine="python")

            return DataFrame(df)

        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return DataFrame(pd.DataFrame({"error": [str(e)]}))
