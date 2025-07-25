import json
from google.cloud import bigquery
from langflow.custom import Component
from langflow.io import FileInput, MessageInput, MessageTextInput
from langflow.template import Output
from langflow.schema import Data

class BigQueryInsertRowDataOnly(Component):
    display_name = "BigQuery Inserter"
    description = "Inserts rows into a Google BigQuery table using structured fields instead of raw JSON."
    icon = "database"
    name = "BigQueryInsertRowDataOnly"

    inputs = [
        FileInput(
            name="gcp_key",
            display_name="GCP Key JSON",
            file_types=["json"],
            info="Attach the service account JSON key for authentication in GCP.",
            required=True
        ),
        MessageTextInput(
            name="project_id",
            display_name="GCP Project ID",
            info="Enter the Google Cloud project ID.",
            required=True
        ),
        MessageTextInput(
            name="dataset_id",
            display_name="Dataset ID",
            info="Enter the BigQuery dataset ID.",
            required=True
        ),
        MessageTextInput(
            name="table_id",
            display_name="Table ID",
            info="Enter the BigQuery table ID.",
            required=True
        ),
        MessageInput(name="timestamp", display_name="Timestamp", info="Timestamp of the record."),
        MessageInput(name="input", display_name="Input", info="User input message."),
        MessageInput(name="phone", display_name="Phone", info="Phone number of the user."),
        MessageInput(name="realm", display_name="Realm", info="Realm or domain information."),
        MessageInput(name="query", display_name="Query", info="Search or user query."),
        MessageInput(name="documentLink", display_name="Document Link", info="URL or link to document."),
        MessageInput(name="output", display_name="Output", info="System response output."),
    ]

    outputs = [
        Output(display_name="Insertion Status", name="status", method="insert_row"),
    ]

    def insert_row(self) -> Data:
        try:
            key_file_path = self.gcp_key

            if not key_file_path or not key_file_path.lower().endswith("json"):
                raise ValueError("Invalid file type. Please upload a valid GCP JSON key.")

            with open(key_file_path, "r") as key_file:
                try:
                    credentials_data = json.load(key_file)
                except json.JSONDecodeError:
                    raise ValueError("The uploaded file is not a valid JSON.")

            client = bigquery.Client.from_service_account_info(credentials_data)
            table_ref = client.dataset(self.dataset_id).table(self.table_id)

            row = {
                "timestamp": self.timestamp.text if self.timestamp else None,
                "input": self.input.text if self.input else None,
                "phone": self.phone.text if self.phone else None,
                "realm": self.realm.text if self.realm else None,
                "query": self.query.text if self.query else None,
                "documentLink": self.documentLink.text if self.documentLink else None,
                "output": self.output.text if self.output else None
            }

            errors = client.insert_rows_json(table_ref, [row])

            if errors:
                return Data(data={"error": f"Failed to insert row: {errors}"})

            return Data(data={"status": "Success", "inserted_rows": 1})

        except Exception as e:
            self.log(f"Error inserting row: {str(e)}")
            return Data(data={"error": str(e)})