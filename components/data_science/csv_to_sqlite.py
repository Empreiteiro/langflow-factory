from langflow.custom import Component
from langflow.io import FileInput, StrInput, Output
from langflow.schema import Data
import pandas as pd
import sqlite3
from pathlib import Path

class CSVtoSQLite(Component):
    display_name = "CSV to SQLite"
    description = "Converts a CSV file into an SQLite database."
    icon = "database"
    name = "CSVtoSQLite"

    inputs = [
        FileInput(
            name="csv_file",
            display_name="CSV File",
            info="Upload the CSV file to convert to SQLite.",
            file_types=["csv"],
            required=True
        ),
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="Name of the table to create in the SQLite database.",
            value="my_table",
        ),
        StrInput(
            name="database_name",
            display_name="Database Name",
            info="Name of the SQLite database file to create (without extension).",
            value="output_db",
        ),
    ]

    outputs = [
        Output(name="database_path", display_name="SQLite DB Path", method="get_database_path")
    ]

    field_order = ["csv_file", "table_name", "database_name"]

    def build(self):
        try:
            if not self.csv_file or not self.csv_file.path:
                raise ValueError("No CSV file provided.")

            csv_path = self.csv_file.path
            df = pd.read_csv(csv_path)

            # Save SQLite file in the same directory as the CSV file
            csv_dir = Path(csv_path).parent
            db_filename = csv_dir / f"{self.database_name}.sqlite"

            conn = sqlite3.connect(db_filename)
            df.to_sql(self.table_name, conn, if_exists='replace', index=False)
            conn.close()

            self.db_path = str(db_filename.resolve())
            self.status = f"Successfully created database at {self.db_path}"

        except Exception as e:
            self.status = f"Error converting CSV to SQLite: {str(e)}"
            self.log(self.status)
            self.db_path = ""

    def get_database_path(self) -> Data:
        if hasattr(self, 'db_path') and self.db_path:
            return Data(text=self.db_path)
        return Data(data={"error": getattr(self, 'status', 'Unknown error')})