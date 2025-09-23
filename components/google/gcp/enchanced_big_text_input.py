import json
import re
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from lfx.custom import Component
from lfx.io import BoolInput, DataInput, FileInput, MessageTextInput, Output, StrInput
from lfx.inputs import SortableListInput
from lfx.schema.dataframe import DataFrame
from lfx.schema import Data


class BigQueryExecutorComponent(Component):
    display_name = "BigQuery"
    description = "Execute SQL queries and perform operations on Google BigQuery."
    name = "BigQueryExecutor"
    icon = "Google"
    beta: bool = True

    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Data input to trigger the BigQuery execution. The data itself is not used in the component.",
            required=False,
        ),
        FileInput(
            name="service_account_json_file",
            display_name="Upload Service Account JSON",
            info="Upload the JSON file containing Google Cloud service account credentials.",
            file_types=["json"],
            required=True,
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="BigQuery operation to perform.",
            options=[
                {"name": "Query", "icon": "search"},
                {"name": "List Datasets", "icon": "database"},
                {"name": "Create Dataset", "icon": "database"},
                {"name": "List Tables", "icon": "table"},
                {"name": "Create Table", "icon": "table"},
                {"name": "Get Table Schema", "icon": "info"},
                {"name": "Delete Table", "icon": "trash"},
                {"name": "Insert Data", "icon": "plus"},
                {"name": "Update Rows", "icon": "edit"},
                {"name": "Query and Update", "icon": "edit"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        MessageTextInput(
            name="query",
            display_name="SQL Query",
            info="The SQL query to execute on BigQuery.",
            required=False,
            tool_mode=True,
            show=False,
        ),
        BoolInput(
            name="clean_query",
            display_name="Clean Query",
            info="When enabled, this will automatically clean up your SQL query.",
            value=False,
            advanced=True,
            show=False,
        ),
        BoolInput(
            name="auto_escape_tables",
            display_name="Auto Escape Table Names",
            info="Automatically add backticks around table names containing hyphens or special characters.",
            value=True,
            advanced=True,
            show=False,
        ),
        MessageTextInput(
            name="table_reference",
            display_name="Table Reference",
            info="Full table reference in format: project.dataset.table or dataset.table (e.g., 'my-project.my_dataset.my_table')",
            required=False,
            tool_mode=True,
            show=False,
        ),
        DataInput(
            name="data_to_insert",
            display_name="Data to Insert",
            info="Data to insert into the table. Should be a list of dictionaries or JSON format.",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="table_schema",
            display_name="Table Schema",
            info="JSON schema for creating a new table. Example: [{'name': 'col1', 'type': 'STRING'}, {'name': 'col2', 'type': 'INTEGER'}]",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="update_condition",
            display_name="Update Condition",
            info="WHERE clause condition for updating rows. Example: 'id = 123' or 'name = \"John\"'",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="field_name",
            display_name="Field Name",
            info="Name of the field to update (e.g., 'ingested', 'status', 'description')",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="field_value",
            display_name="Field Value",
            info="New value for the field. For BOOLEAN: use 'TRUE'/'FALSE'. For TIMESTAMP: use 'NOW()' or date string. For other types: provide the value directly.",
            required=False,
            tool_mode=True,
            show=False,
        ),
        StrInput(
            name="dataset_description",
            display_name="Dataset Description",
            info="Description for the new dataset.",
            required=False,
            show=False,
        ),
        StrInput(
            name="dataset_location",
            display_name="Dataset Location",
            info="Location for the dataset (e.g., 'US', 'EU', 'asia-northeast1').",
            value="US",
            required=False,
            show=False,
        ),
        # New inputs for Query and Update functionality
        MessageTextInput(
            name="select_query",
            display_name="SQL Query",
            info="SQL query to identify which rows to update. ALL columns returned by this query will be used as criteria to precisely match and update only the exact rows found (using WHERE clause with AND conditions for all columns).",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="update_field_name",
            display_name="Field Name",
            info="Name of the field to update in Query and Update operation (e.g., 'ingested', 'status', 'updated')",
            required=False,
            tool_mode=True,
            show=False,
        ),
        MessageTextInput(
            name="update_field_value",
            display_name="Field Value",
            info="Value to set in the specified field for all rows returned by the query. For BOOLEAN: use 'TRUE'/'FALSE'. For TIMESTAMP: use 'NOW()' or date string.",
            required=False,
            tool_mode=True,
            show=False,
        ),
    ]

    outputs = [
        Output(display_name="Results", name="results", method="execute_action"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Query": ["query", "clean_query", "auto_escape_tables"],
            "List Datasets": [],
            "List Tables": ["table_reference"],
            "Insert Data": ["table_reference", "data_to_insert"],
            "Update Rows": ["table_reference", "update_condition", "field_name", "field_value"],
            "Create Dataset": ["table_reference", "dataset_description", "dataset_location"],
            "Create Table": ["table_reference", "table_schema"],
            "Delete Table": ["table_reference"],
            "Get Table Schema": ["table_reference"],
            "Query and Update": ["table_reference", "select_query", "update_field_name", "update_field_value"],
        }

        # Hide all dynamic fields first
        for field_name in ["query", "clean_query", "auto_escape_tables", "table_reference", "data_to_insert",
                          "table_schema", "dataset_description", "dataset_location", "update_condition", 
                          "field_name", "field_value", "select_query", "update_field_name", "update_field_value"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Update outputs dynamically based on selected action."""
        if field_name == "action":
            # Extract action name from the selected action
            selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []
            
            # Clear existing outputs
            frontend_node["outputs"] = []
            
            if len(selected) == 1:
                action_name = selected[0]
                
                if action_name == "Query":
                    # For Query action, return DataFrame directly
                    frontend_node["outputs"].append(
                        Output(display_name="DataFrame", name="dataframe", method="execute_query_dataframe")
                    )
                elif action_name == "Query and Update":
                    # For Query and Update action, return DataFrame with queried and updated data
                    frontend_node["outputs"].append(
                        Output(display_name="DataFrame", name="dataframe", method="execute_query_and_update_dataframe")
                    )
                else:
                    # For all other actions, return Data
                    frontend_node["outputs"].append(
                        Output(display_name="Results", name="results", method="execute_action")
                    )
            else:
                # Default output when no action is selected
                frontend_node["outputs"].append(
                    Output(display_name="Results", name="results", method="execute_action")
                )
        
        return frontend_node

    def execute_action(self) -> Data:
        try:
            # First try to read the file and setup credentials
            try:
                service_account_path = Path(self.service_account_json_file)
                with service_account_path.open() as f:
                    credentials_json = json.load(f)
                    project_id = credentials_json.get("project_id")
                    if not project_id:
                        msg = "No project_id found in service account credentials file."
                        raise ValueError(msg)
            except FileNotFoundError as e:
                msg = f"Service account file not found: {e}"
                raise ValueError(msg) from e
            except json.JSONDecodeError as e:
                msg = "Invalid JSON string for service account credentials"
                raise ValueError(msg) from e

            # Load credentials
            try:
                credentials = Credentials.from_service_account_file(self.service_account_json_file)
                client = bigquery.Client(credentials=credentials, project=project_id)
            except Exception as e:
                msg = f"Error loading service account credentials: {e}"
                raise ValueError(msg) from e

        except ValueError:
            raise
        except Exception as e:
            msg = f"Error setting up BigQuery client: {e}"
            raise ValueError(msg) from e

        # Get the selected action
        if not hasattr(self, 'action') or not self.action:
            return Data(data={"error": "Action is required"})

        action_name = None
        if isinstance(self.action, list) and len(self.action) > 0:
            action_name = self.action[0].get("name")
        elif isinstance(self.action, dict):
            action_name = self.action.get("name")
        
        if not action_name:
            return Data(data={"error": "Invalid action selected"})

        try:
            # Execute the appropriate action
            if action_name == "Query":
                # Query action is handled by execute_query_dataframe method via dynamic output
                return Data(data={"message": "Query action handled by DataFrame output"})
            elif action_name == "List Datasets":
                return self._list_datasets(client)
            elif action_name == "List Tables":
                return self._list_tables(client)
            elif action_name == "Insert Data":
                return self._insert_data(client, project_id)
            elif action_name == "Update Rows":
                return self._update_rows(client, project_id)
            elif action_name == "Create Dataset":
                return self._create_dataset(client, project_id)
            elif action_name == "Create Table":
                return self._create_table(client, project_id)
            elif action_name == "Delete Table":
                return self._delete_table(client, project_id)
            elif action_name == "Get Table Schema":
                return self._get_table_schema(client, project_id)
            elif action_name == "Query and Update":
                return self._query_and_update(client, project_id)
            else:
                return Data(data={"error": f"Unsupported action: {action_name}"})

        except RefreshError as e:
            msg = "Authentication error: Unable to refresh authentication token. Please try to reauthenticate."
            return Data(data={"error": msg})
        except Exception as e:
            msg = f"Error executing BigQuery action '{action_name}': {e}"
            return Data(data={"error": msg})

    def execute_query_dataframe(self) -> DataFrame:
        """Execute SQL query and return DataFrame directly for dynamic output."""
        try:
            # First try to read the file and setup credentials
            try:
                service_account_path = Path(self.service_account_json_file)
                with service_account_path.open() as f:
                    credentials_json = json.load(f)
                    project_id = credentials_json.get("project_id")
                    if not project_id:
                        msg = "No project_id found in service account credentials file."
                        raise ValueError(msg)
            except FileNotFoundError as e:
                msg = f"Service account file not found: {e}"
                raise ValueError(msg) from e
            except json.JSONDecodeError as e:
                msg = "Invalid JSON string for service account credentials"
                raise ValueError(msg) from e

            # Load credentials
            try:
                credentials = Credentials.from_service_account_file(self.service_account_json_file)
                client = bigquery.Client(credentials=credentials, project=project_id)
            except Exception as e:
                msg = f"Error loading service account credentials: {e}"
                raise ValueError(msg) from e

        except ValueError:
            raise
        except Exception as e:
            msg = f"Error setting up BigQuery client: {e}"
            raise ValueError(msg) from e

        # Execute the query using the existing method
        return self._execute_query(client)

    def execute_query_and_update_dataframe(self) -> DataFrame:
        """Execute query and update operation and return DataFrame with queried data."""
        try:
            # First try to read the file and setup credentials
            try:
                service_account_path = Path(self.service_account_json_file)
                with service_account_path.open() as f:
                    credentials_json = json.load(f)
                    project_id = credentials_json.get("project_id")
                    if not project_id:
                        msg = "No project_id found in service account credentials file."
                        raise ValueError(msg)
            except FileNotFoundError as e:
                msg = f"Service account file not found: {e}"
                raise ValueError(msg) from e
            except json.JSONDecodeError as e:
                msg = "Invalid JSON string for service account credentials"
                raise ValueError(msg) from e

            # Load credentials
            try:
                credentials = Credentials.from_service_account_file(self.service_account_json_file)
                client = bigquery.Client(credentials=credentials, project=project_id)
            except Exception as e:
                msg = f"Error loading service account credentials: {e}"
                raise ValueError(msg) from e

        except ValueError:
            raise
        except Exception as e:
            msg = f"Error setting up BigQuery client: {e}"
            raise ValueError(msg) from e

        # Execute the query and update using the existing method
        return self._execute_query_and_update_dataframe(client, project_id)

    def _execute_query(self, client) -> DataFrame:
        # Check for empty or whitespace-only query before cleaning
        if not str(self.query).strip():
            msg = "No valid SQL query found in input text."
            raise ValueError(msg)

        original_query = str(self.query)
        
        # Clean the query more intelligently
        if "```" in original_query:
            # Only clean if there are code blocks
            sql_query = self._clean_sql_query(original_query)
            self.log(f"Query cleaned from {len(original_query)} to {len(sql_query)} characters")
        elif self.clean_query:
            # Clean if explicitly requested
            sql_query = self._clean_sql_query(original_query)
            self.log(f"Query cleaned from {len(original_query)} to {len(sql_query)} characters")
        else:
            # For most SQL queries, just strip whitespace - this preserves the original query
            sql_query = original_query.strip()
            self.log("Using query as-is (no cleaning applied)")

        # Auto-escape table names if requested
        if getattr(self, 'auto_escape_tables', True):
            sql_query = self._auto_escape_table_names(sql_query)
            self.log("Applied auto-escaping to table names")

        # Log the final query for debugging (truncated if too long)
        query_preview = sql_query[:200] + "..." if len(sql_query) > 200 else sql_query
        self.log(f"Executing query: {query_preview}")

        try:
            # Execute the query
            query_job = client.query(sql_query)
            
            # Wait for the job to complete and get results
            results = query_job.result()
            
            # Convert results to list of dictionaries
            output_dict = []
            for row in results:
                # Convert BigQuery Row to dict, handling different data types
                row_dict = {}
                for key, value in row.items():
                    # Handle BigQuery specific data types
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[key] = value.isoformat()
                    elif value is None:
                        row_dict[key] = None
                    else:
                        row_dict[key] = value
                output_dict.append(row_dict)
            
            self.log(f"Query executed successfully. Returned {len(output_dict)} rows.")
            
        except Exception as e:
            # Enhanced error reporting
            error_msg = str(e)
            
            # Check for common SQL errors and provide helpful hints
            if "Syntax error" in error_msg:
                if "Unclosed string literal" in error_msg:
                    hint = " (Hint: Check for unmatched quotes in your query)"
                elif "Unexpected keyword" in error_msg:
                    hint = " (Hint: Check SQL syntax and reserved keywords)"
                else:
                    hint = " (Hint: Review your SQL syntax)"
                error_msg += hint
            elif "Table" in error_msg and "not found" in error_msg:
                error_msg += " (Hint: Verify table name and project ID)"
            elif "Access Denied" in error_msg:
                error_msg += " (Hint: Check your service account permissions)"
            
            # Include the cleaned query in error for debugging
            if len(sql_query) <= 500:
                error_msg += f"\n\nQuery attempted:\n{sql_query}"
            else:
                error_msg += f"\n\nQuery attempted (first 500 chars):\n{sql_query[:500]}..."
            
            raise ValueError(f"Error executing BigQuery SQL query: {error_msg}") from e

        return DataFrame(output_dict)

    def _list_datasets(self, client) -> Data:
        datasets = list(client.list_datasets())
        dataset_list = []
        for dataset in datasets:
            dataset_dict = {
                "dataset_id": dataset.dataset_id,
                "project": dataset.project,
                "full_dataset_id": dataset.full_dataset_id,
            }
            
            # Only add attributes that exist
            if hasattr(dataset, 'description') and dataset.description:
                dataset_dict["description"] = dataset.description
            if hasattr(dataset, 'location') and dataset.location:
                dataset_dict["location"] = dataset.location
            if hasattr(dataset, 'created') and dataset.created:
                dataset_dict["created"] = dataset.created.isoformat()
            if hasattr(dataset, 'modified') and dataset.modified:
                dataset_dict["modified"] = dataset.modified.isoformat()
                
            dataset_list.append(dataset_dict)
        
        return Data(data={"datasets": dataset_list, "total_datasets": len(dataset_list)})

    def _list_tables(self, client) -> Data:
        table_reference = getattr(self, 'table_reference', None)
        if not table_reference:
            return Data(data={"error": "Table Reference is required for listing tables (use format: dataset or project.dataset)"})

        try:
            # Extract dataset from table reference
            parts = table_reference.strip().split('.')
            if len(parts) == 1:
                # Only dataset provided
                dataset_id = parts[0]
            elif len(parts) == 2:
                # project.dataset format
                dataset_id = parts[1]
            elif len(parts) == 3:
                # project.dataset.table format
                dataset_id = parts[1]
            else:
                return Data(data={"error": "Invalid table reference format. Use: dataset, project.dataset, or project.dataset.table"})

            dataset = client.dataset(dataset_id)
            tables = list(client.list_tables(dataset))
            table_list = []
            for table in tables:
                table_dict = {
                    "table_id": table.table_id,
                    "dataset_id": table.dataset_id,
                    "project": table.project,
                    "full_table_id": table.full_table_id,
                }
                
                # Only add attributes that exist
                if hasattr(table, 'table_type') and table.table_type:
                    table_dict["table_type"] = table.table_type
                if hasattr(table, 'created') and table.created:
                    table_dict["created"] = table.created.isoformat()
                if hasattr(table, 'modified') and table.modified:
                    table_dict["modified"] = table.modified.isoformat()
                if hasattr(table, 'num_rows') and table.num_rows is not None:
                    table_dict["num_rows"] = table.num_rows
                if hasattr(table, 'num_bytes') and table.num_bytes is not None:
                    table_dict["num_bytes"] = table.num_bytes
                    
                table_list.append(table_dict)
            
            return Data(data={"tables": table_list, "total_tables": len(table_list)})
        except Exception as e:
            return Data(data={"error": f"Error listing tables in dataset '{dataset_id}': {str(e)}"})

    def _insert_data(self, client, project_id) -> Data:
        dataset_id = getattr(self, 'dataset_id', None)
        table_id = getattr(self, 'table_id', None)
        data_to_insert = getattr(self, 'data_to_insert', None)

        if not dataset_id:
            return Data(data={"error": "Dataset ID is required for inserting data"})
        if not table_id:
            return Data(data={"error": "Table ID is required for inserting data"})
        if not data_to_insert:
            return Data(data={"error": "Data to insert is required"})

        try:
            # Process the data input
            if hasattr(data_to_insert, 'data'):
                insert_data = data_to_insert.data
            elif isinstance(data_to_insert, str):
                insert_data = json.loads(data_to_insert)
            else:
                insert_data = data_to_insert

            # Ensure data is a list
            if not isinstance(insert_data, list):
                insert_data = [insert_data]

            table_ref = client.dataset(dataset_id).table(table_id)
            table = client.get_table(table_ref)
            
            errors = client.insert_rows_json(table, insert_data)
            
            if errors:
                return Data(data={"error": f"Insertion errors: {errors}"})
            else:
                return Data(data={"success": True, "inserted_rows": len(insert_data), "message": f"Successfully inserted {len(insert_data)} rows"})

        except Exception as e:
            return Data(data={"error": f"Error inserting data: {str(e)}"})

    def _create_dataset(self, client, project_id) -> Data:
        dataset_id = getattr(self, 'dataset_id', None)
        dataset_description = getattr(self, 'dataset_description', '')
        dataset_location = getattr(self, 'dataset_location', 'US')

        if not dataset_id:
            return Data(data={"error": "Dataset ID is required for creating dataset"})

        try:
            dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
            dataset.location = dataset_location
            if dataset_description:
                dataset.description = dataset_description

            dataset = client.create_dataset(dataset, timeout=30)
            
            return Data(data={
                "success": True, 
                "dataset_id": dataset.dataset_id,
                "full_dataset_id": dataset.full_dataset_id,
                "location": dataset.location,
                "message": f"Successfully created dataset '{dataset_id}'"
            })

        except Exception as e:
            return Data(data={"error": f"Error creating dataset: {str(e)}"})

    def _create_table(self, client, project_id) -> Data:
        dataset_id = getattr(self, 'dataset_id', None)
        table_id = getattr(self, 'table_id', None)
        table_schema = getattr(self, 'table_schema', None)

        if not dataset_id:
            return Data(data={"error": "Dataset ID is required for creating table"})
        if not table_id:
            return Data(data={"error": "Table ID is required for creating table"})
        if not table_schema:
            return Data(data={"error": "Table schema is required for creating table"})

        try:
            # Parse schema
            if isinstance(table_schema, str):
                schema_data = json.loads(table_schema)
            else:
                schema_data = table_schema

            # Convert to BigQuery schema format
            schema = []
            for field in schema_data:
                schema.append(bigquery.SchemaField(
                    field['name'], 
                    field['type'],
                    mode=field.get('mode', 'NULLABLE'),
                    description=field.get('description', '')
                ))

            table_ref = client.dataset(dataset_id).table(table_id)
            table = bigquery.Table(table_ref, schema=schema)
            
            table = client.create_table(table)
            
            return Data(data={
                "success": True,
                "table_id": table.table_id,
                "full_table_id": table.full_table_id,
                "schema_length": len(schema),
                "message": f"Successfully created table '{table_id}'"
            })

        except Exception as e:
            return Data(data={"error": f"Error creating table: {str(e)}"})

    def _delete_table(self, client, project_id) -> Data:
        dataset_id = getattr(self, 'dataset_id', None)
        table_id = getattr(self, 'table_id', None)

        if not dataset_id:
            return Data(data={"error": "Dataset ID is required for deleting table"})
        if not table_id:
            return Data(data={"error": "Table ID is required for deleting table"})

        try:
            table_ref = client.dataset(dataset_id).table(table_id)
            client.delete_table(table_ref, not_found_ok=True)
            
            return Data(data={
                "success": True,
                "message": f"Successfully deleted table '{dataset_id}.{table_id}'"
            })

        except Exception as e:
            return Data(data={"error": f"Error deleting table: {str(e)}"})

    def _get_table_schema(self, client, project_id) -> Data:
        dataset_id = getattr(self, 'dataset_id', None)
        table_id = getattr(self, 'table_id', None)

        if not dataset_id:
            return Data(data={"error": "Dataset ID is required for getting table schema"})
        if not table_id:
            return Data(data={"error": "Table ID is required for getting table schema"})

        try:
            table_ref = client.dataset(dataset_id).table(table_id)
            table = client.get_table(table_ref)
            
            schema_info = []
            for field in table.schema:
                schema_info.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                })
            
            return Data(data={
                "table_id": table.table_id,
                "full_table_id": table.full_table_id,
                "schema": schema_info,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None
            })

        except Exception as e:
            return Data(data={"error": f"Error getting table schema: {str(e)}"})

    def _update_rows(self, client, project_id) -> Data:
        table_reference = getattr(self, 'table_reference', None)
        update_condition = getattr(self, 'update_condition', None)
        field_name = getattr(self, 'field_name', None)
        field_value = getattr(self, 'field_value', None)

        if not table_reference:
            return Data(data={"error": "Table Reference is required for updating rows"})
        if not update_condition:
            return Data(data={"error": "Update condition (WHERE clause) is required for updating rows"})
        if not field_name:
            return Data(data={"error": "Field Name is required for updating rows"})
        if field_value is None or str(field_value).strip() == '':
            return Data(data={"error": "Field Value is required for updating rows"})

        try:
            # Clean and format the table reference
            table_ref = table_reference.strip()
            if not table_ref.startswith('`') and not table_ref.endswith('`'):
                # Add backticks if not already present
                table_ref = f"`{table_ref}`"

            # Process the WHERE condition to handle quotes properly
            condition = str(update_condition).strip()
            
            # If the condition contains double quotes, convert them to single quotes for BigQuery
            if '"' in condition:
                # Replace double quotes with single quotes for string literals in SQL
                condition = condition.replace('"', "'")
                self.log(f"Converted WHERE condition quotes: {condition}")

            # Format the field value based on type
            formatted_value = self._format_field_value(field_value)
            
            # Build the SET clause
            set_clauses = [f"`{field_name}` = {formatted_value}"]

            # Build the full UPDATE query
            set_clause = ", ".join(set_clauses)
            update_query = f"UPDATE {table_ref} SET {set_clause} WHERE {condition}"

            # Log the query for debugging
            self.log(f"Executing UPDATE query: {update_query}")

            # Execute the UPDATE query
            query_job = client.query(update_query)
            query_job.result()  # Wait for the job to complete

            # Get the number of affected rows
            affected_rows = query_job.num_dml_affected_rows if hasattr(query_job, 'num_dml_affected_rows') else 0

            return Data(data={
                "success": True,
                "affected_rows": affected_rows,
                "query_executed": update_query,
                "field_updated": field_name,
                "field_value": field_value,
                "table_reference": table_reference,
                "message": f"Successfully updated field '{field_name}' in {affected_rows} rows in table '{table_reference}'"
            })

        except Exception as e:
            # Enhanced error reporting
            error_msg = str(e)
            
            # Check for common UPDATE errors and provide helpful hints
            if "Syntax error" in error_msg:
                error_msg += " (Hint: Check your WHERE condition syntax and table reference format)"
            elif "Column" in error_msg and "not found" in error_msg:
                error_msg += " (Hint: Verify that the specified field names exist in the table)"
            elif "Table" in error_msg and "not found" in error_msg:
                error_msg += " (Hint: Verify table reference format: project.dataset.table or dataset.table)"
            elif "Access Denied" in error_msg:
                error_msg += " (Hint: Check your service account permissions for UPDATE operations)"
            
            # Include the generated query in the error message
            full_error_msg = f"Error updating fields: {error_msg}\n\nGenerated Query:\n{update_query}"
            
            return Data(data={"error": full_error_msg, "query": update_query})

    def _execute_query_and_update_dataframe(self, client, project_id) -> DataFrame:
        """Execute a query first, then update the specified fields for precisely matched rows using ALL query columns as criteria, and return the queried data as DataFrame."""
        try:
            table_reference = getattr(self, 'table_reference', None)
            select_query = getattr(self, 'select_query', None)
            update_field_name = getattr(self, 'update_field_name', None)
            update_field_value = getattr(self, 'update_field_value', None)

            if not table_reference:
                raise ValueError("Table Reference is required for query and update operation")
            if not select_query or not select_query.strip():
                raise ValueError("SQL Query is required for query and update operation")
            if not update_field_name:
                raise ValueError("Field Name is required for query and update operation")
            if update_field_value is None or str(update_field_value).strip() == '':
                raise ValueError("Field Value is required for query and update operation")

            # Step 1: Execute the SELECT query
            query_results = []
            try:
                # Clean the query if needed
                if "```" in select_query:
                    cleaned_query = self._clean_sql_query(select_query)
                else:
                    cleaned_query = select_query.strip()

                # Auto-escape table names if requested
                if getattr(self, 'auto_escape_tables', True):
                    cleaned_query = self._auto_escape_table_names(cleaned_query)

                self.log(f"Executing query: {cleaned_query}")
                query_job = client.query(cleaned_query)
                query_results_raw = query_job.result()
                
                # Convert results to list of dictionaries (same format as _execute_query)
                for row in query_results_raw:
                    row_dict = {}
                    for key, value in row.items():
                        # Handle BigQuery specific data types
                        if hasattr(value, 'isoformat'):  # datetime objects
                            row_dict[key] = value.isoformat()
                        elif value is None:
                            row_dict[key] = None
                        else:
                            row_dict[key] = value
                    query_results.append(row_dict)
                
                self.log(f"Query executed successfully. Returned {len(query_results)} rows.")
                
                if not query_results:
                    self.log("Query executed but returned no results.")
                    raise ValueError("Query returned no results to use for update")
                    
            except Exception as e:
                error_msg = f"Query execution failed: {str(e)}"
                
                # Include the query in the error message
                if 'cleaned_query' in locals():
                    error_msg += f"\n\nQuery attempted:\n{cleaned_query}"
                
                raise ValueError(error_msg)

            # Step 2: Update the specified fields for each row returned by the query
            try:
                # Clean and format the table reference
                table_ref = table_reference.strip()
                if not table_ref.startswith('`'):
                    # Add backticks if not already present
                    table_ref = f"`{table_ref}`"

                # Format the field value based on type
                formatted_value = self._format_field_value(update_field_value)
                
                # Get table schema to detect field types for better formatting
                try:
                    # Remove backticks for client.get_table() call
                    clean_table_ref = table_ref.strip('`')
                    table = client.get_table(clean_table_ref)
                    field_types = {}
                    for field in table.schema:
                        field_types[field.name.lower()] = field.field_type
                    
                    self.log(f"Detected field types: {field_types}")
                    
                except Exception as schema_error:
                    self.log(f"Could not detect field types: {schema_error}")
                    field_types = {}

                # Get all column names from the query results
                all_columns = list(query_results[0].keys()) if query_results else []
                if not all_columns:
                    raise ValueError("Query results must include at least one column to identify rows for update")
                
                # Detect key columns for WHERE clause (prefer unique identifiers)
                key_columns = self._detect_key_columns(all_columns)
                self.log(f"Query returned columns: {all_columns}")
                self.log(f"Using key columns as criteria for updates: {key_columns}")
                self.log(f"Field to update: {update_field_name}")
                
                # Optimize: Use a single UPDATE query with a subquery instead of row-by-row updates
                # This approach uses the original query as a subquery to identify rows to update
                
                # Clean the original query to use as subquery
                subquery = cleaned_query.strip()
                if subquery.endswith(';'):
                    subquery = subquery[:-1]  # Remove trailing semicolon
                
                # Build the optimized UPDATE query using the original query as a subquery
                # We'll use EXISTS with the subquery to match rows
                where_conditions = []
                for column_name in key_columns:
                    where_conditions.append(f"main_table.`{column_name}` = sub_query.`{column_name}`")
                
                where_clause = " AND ".join(where_conditions)
                
                # Create the optimized UPDATE query
                optimized_update_query = f"""
UPDATE {table_ref} AS main_table
SET `{update_field_name}` = {formatted_value}
WHERE EXISTS (
    SELECT 1 
    FROM ({subquery}) AS sub_query
    WHERE {where_clause}
)"""
                
                self.log(f"Executing optimized bulk update query: {optimized_update_query}")
                
                # Execute the single bulk update
                update_job = client.query(optimized_update_query)
                update_job.result()  # Wait for the job to complete
                
                # Get the number of affected rows
                total_affected_rows = update_job.num_dml_affected_rows if hasattr(update_job, 'num_dml_affected_rows') else len(query_results)
                
                self.log(f"Bulk update completed successfully. Total affected rows: {total_affected_rows}")
                
            except Exception as e:
                error_msg = f"Bulk update execution failed: {str(e)}"
                
                # Enhanced error reporting
                if "Syntax error" in error_msg:
                    error_msg += " (Hint: Check your table reference format and query structure)"
                elif "Column" in error_msg and "not found" in error_msg:
                    error_msg += " (Hint: Verify that the specified field names exist in the table, or check that all column names from your query exist in the target table)"
                elif "cannot be assigned" in error_msg.lower() and "type" in error_msg.lower():
                    error_msg += " (Hint: Check the data types of the fields being updated. For BOOLEAN fields use 'true'/'false', for TIMESTAMP fields use NOW() or a date string)"
                elif "Table" in error_msg and "not found" in error_msg:
                    error_msg += " (Hint: Verify table reference format: project.dataset.table)"
                elif "Access Denied" in error_msg:
                    error_msg += " (Hint: Check your service account permissions for UPDATE operations)"

                # Include the generated query in the error message
                error_msg += f"\n\nGenerated Query:\n{optimized_update_query if 'optimized_update_query' in locals() else 'Query not available'}"
                
                self.log(error_msg)
                raise ValueError(error_msg)

            # Return the query results as DataFrame (same format as regular query)
            return DataFrame(query_results)

        except Exception as e:
            error_msg = f"Error in query and update operation: {str(e)}"
            self.log(error_msg)
            raise ValueError(error_msg)

    def _query_and_update(self, client, project_id) -> Data:
        """Execute a query first, then update specified fields using query results."""
        try:
            table_reference = getattr(self, 'table_reference', None)
            select_query = getattr(self, 'select_query', None)
            update_field_name = getattr(self, 'update_field_name', None)
            update_field_value = getattr(self, 'update_field_value', None)

            if not table_reference:
                return Data(data={"error": "Table Reference is required for query and update operation"})
            if not select_query or not select_query.strip():
                return Data(data={"error": "SQL Query is required for query and update operation"})
            if not update_field_name:
                return Data(data={"error": "Field Name is required for query and update operation"})
            if update_field_value is None or str(update_field_value).strip() == '':
                return Data(data={"error": "Field Value is required for query and update operation"})

            # Step 1: Execute the SELECT query
            query_results = None
            column_names = []
            try:
                # Clean the query if needed
                if "```" in select_query:
                    cleaned_query = self._clean_sql_query(select_query)
                else:
                    cleaned_query = select_query.strip()

                # Auto-escape table names if requested
                if getattr(self, 'auto_escape_tables', True):
                    cleaned_query = self._auto_escape_table_names(cleaned_query)

                self.log(f"Executing query: {cleaned_query}")
                query_job = client.query(cleaned_query)
                query_results = list(query_job.result())
                
                # Get column names from the first row (if any results)
                if query_results:
                    column_names = list(query_results[0].keys())
                    self.log(f"Query executed successfully. Returned {len(query_results)} rows with columns: {column_names}")
                else:
                    self.log("Query executed but returned no results.")
                    return Data(data={"error": "Query returned no results to use for update"})
                    
            except Exception as e:
                error_msg = f"Query execution failed: {str(e)}"
                
                # Include the query in the error message
                if 'cleaned_query' in locals():
                    error_msg += f"\n\nQuery attempted:\n{cleaned_query}"
                
                return Data(data={"error": error_msg})

            # Step 2: Update specified fields
            if not query_results:
                return Data(data={"error": "No query results available for update operation"})

            # Clean and format the table reference
            table_ref = table_reference.strip()
            if not table_ref.startswith('`'):
                # Add backticks if not already present
                table_ref = f"`{table_ref}`"

            # Call the dataframe method and capture key column info for feedback
            try:
                # We'll call the dataframe method which has the key column detection logic
                df_result = self._execute_query_and_update_dataframe(client, project_id)
                total_affected_rows = len(df_result.data) if hasattr(df_result, 'data') else 0
                
                # Try to get column info from the result for better feedback
                key_columns_info = ""
                if hasattr(df_result, 'data') and df_result.data:
                    all_columns = list(df_result.data[0].keys()) if df_result.data else []
                    key_columns = self._detect_key_columns(all_columns)
                    if len(key_columns) < len(all_columns):
                        key_columns_info = f" Using key columns {key_columns} to identify rows."
                
                return Data(data={
                    "success": True,
                    "query_executed": True,
                    "update_executed": True,
                    "total_affected_rows": total_affected_rows,
                    "field_updated": update_field_name,
                    "field_value": update_field_value,
                    "table_reference": table_reference,
                    "message": f"Successfully updated field '{update_field_name}' in {total_affected_rows} rows in table '{table_reference}'.{key_columns_info}"
                })
                
            except Exception as e:
                error_msg = f"Query and update operation failed: {str(e)}"
                self.log(error_msg)
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = f"Error in query and update operation: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _detect_key_columns(self, all_columns):
        """Detect which columns to use as key identifiers for WHERE clauses.
        
        Prioritizes unique identifiers and avoids frequently changing fields.
        
        Args:
            all_columns: List of all column names from query results
            
        Returns:
            List of column names to use as key identifiers
        """
        if not all_columns:
            return all_columns
        
        # Priority 1: Common unique identifier field names
        unique_identifiers = ['id', 'uuid', 'primary_key', 'pk', 'key', 'row_id']
        for identifier in unique_identifiers:
            if identifier in all_columns:
                return [identifier]
        
        # Priority 2: Fields ending with '_id' (likely foreign keys or identifiers)
        id_fields = [col for col in all_columns if col.lower().endswith('_id')]
        if id_fields:
            return id_fields[:2]  # Use up to 2 ID fields
        
        # Priority 3: Fields that look like identifiers or stable references
        stable_fields = []
        for col in all_columns:
            col_lower = col.lower()
            # Include fields that are likely stable identifiers
            if any(keyword in col_lower for keyword in ['name', 'code', 'reference', 'path', 'url', 'repository']):
                stable_fields.append(col)
        
        if stable_fields:
            return stable_fields[:3]  # Use up to 3 stable fields
        
        # Priority 4: Exclude commonly changing fields and use the rest
        exclude_patterns = ['timestamp', 'date', 'time', 'modified', 'updated', 'created', 
                          'description', 'content', 'text', 'body', 'message', 'comment']
        
        key_fields = []
        for col in all_columns:
            col_lower = col.lower()
            if not any(pattern in col_lower for pattern in exclude_patterns):
                key_fields.append(col)
        
        if key_fields:
            return key_fields[:3]  # Use up to 3 non-changing fields
        
        # Fallback: Use first 2 columns as a last resort
        return all_columns[:2]

    def _format_field_value(self, field_value):
        """Format a field value for BigQuery with automatic type detection.
        
        Args:
            field_value: The value to format
            
        Returns:
            Formatted value string for SQL query
        """
        # Handle None values
        if field_value is None:
            return "NULL"
        
        # Handle different value types
        if isinstance(field_value, str):
            # SQL Functions (highest priority)
            if field_value.upper() in ['NOW()', 'CURRENT_TIMESTAMP()', 'CURRENT_TIMESTAMP']:
                return field_value.upper()
            
            # Auto-detect boolean strings
            if field_value.upper() in ['TRUE', 'FALSE']:
                return field_value.upper()
            
            # Handle other common boolean representations
            if field_value.upper() in ['1', 'YES', 'Y', 'T']:
                return "TRUE"
            elif field_value.upper() in ['0', 'NO', 'N', 'F']:
                return "FALSE"
            
            # Regular string value - escape single quotes
            else:
                escaped_value = str(field_value).replace("'", "''")
                return f"'{escaped_value}'"
        
        elif isinstance(field_value, bool):
            return "TRUE" if field_value else "FALSE"
        
        elif isinstance(field_value, (int, float)):
            return str(field_value)
        
        else:
            # For any other type, convert to string and wrap in quotes
            escaped_value = str(field_value).replace("'", "''")
            return f"'{escaped_value}'"

    # Keep the existing _clean_sql_query method
    def _clean_sql_query(self, query: str) -> str:
        """Clean SQL query by removing surrounding quotes and whitespace.

        Also extracts SQL statements from text that might contain other content.

        Args:
            query: The SQL query to clean

        Returns:
            The cleaned SQL query
        """
        original_query = query
        
        # First, try to extract SQL from code blocks
        sql_pattern = r"```(?:sql)?\s*([\s\S]*?)\s*```"
        sql_matches = re.findall(sql_pattern, query, re.IGNORECASE | re.DOTALL)

        if sql_matches:
            # If we found SQL in code blocks, use the first match
            query = sql_matches[0]
        else:
            # If no code block, check if the query starts with common SQL keywords
            # If it does, it's probably already a clean query
            sql_keywords = r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|MERGE)"
            if re.match(sql_keywords, query.strip(), re.IGNORECASE):
                # Already looks like a clean SQL query, just strip whitespace
                return query.strip()
            
            # Try to find SQL statements by looking for lines that start with SQL keywords
            lines = query.split("\n")
            sql_lines = []
            in_sql = False

            for line in lines:
                stripped_line = line.strip()
                if re.match(sql_keywords, stripped_line, re.IGNORECASE):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)  # Keep original formatting/indentation
                if stripped_line.endswith(";"):
                    in_sql = False

            if sql_lines:
                query = "\n".join(sql_lines)
            else:
                # If we can't find SQL patterns, return the original query stripped
                return original_query.strip()

        # Remove any backticks that might be at the very start or end (not part of table names)
        query = query.strip()
        if query.startswith("```") or query.endswith("```"):
            query = query.strip("`")

        # Only remove surrounding quotes if they wrap the ENTIRE query
        query = query.strip()
        if len(query) > 2:
            if (query.startswith('"') and query.endswith('"') and query.count('"') == 2) or \
               (query.startswith("'") and query.endswith("'") and query.count("'") == 2):
                query = query[1:-1]

        # Return the cleaned query, preserving internal formatting
        return query.strip()

    def _auto_escape_table_names(self, query: str) -> str:
        """Automatically add backticks around table names that need escaping."""
        import re
        
        def escape_table_reference(table_ref: str) -> str:
            """Escape individual table reference if it contains hyphens."""
            # Skip if already escaped
            if table_ref.startswith('`') and table_ref.endswith('`'):
                return table_ref
                
            parts = table_ref.split('.')
            escaped_parts = []
            
            for part in parts:
                # Escape if contains hyphens, starts with number, or is a reserved word
                if ('-' in part or 
                    (part and part[0].isdigit()) or 
                    part.upper() in ['ORDER', 'GROUP', 'SELECT', 'FROM', 'WHERE', 'JOIN']):
                    escaped_parts.append(f'`{part}`')
                else:
                    escaped_parts.append(part)
            
            return '.'.join(escaped_parts)
        
        # Pattern to find table references in FROM clauses
        # Matches: FROM table_name or FROM project.dataset.table
        from_pattern = r'FROM\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)'
        
        def replace_from_table(match):
            table_ref = match.group(1)
            escaped = escape_table_reference(table_ref)
            return f"FROM {escaped}"
        
        query = re.sub(from_pattern, replace_from_table, query, flags=re.IGNORECASE)
        
        # Pattern to find table references in JOIN clauses
        join_pattern = r'JOIN\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)'
        
        def replace_join_table(match):
            table_ref = match.group(1)
            escaped = escape_table_reference(table_ref)
            return f"JOIN {escaped}"
        
        query = re.sub(join_pattern, replace_join_table, query, flags=re.IGNORECASE)
        
        return query
