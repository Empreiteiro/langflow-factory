from typing import Any, Dict
import pandas as pd
from langflow.custom import Component
from langflow.io import (
    FileInput,
    StrInput,
    IntInput,
    BoolInput,
    DropdownInput,
    DataInput,
    MessageTextInput,
    MessageInput,
    Output,
)
from langflow.inputs import SortableListInput
from langflow.schema import Data
import json

# Handle optional dependencies
GOOGLE_SHEETS_AVAILABLE = False
service_account = None
build = None

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    pass


class GoogleSheetsToolComponent(Component):
    display_name = "Google Sheets Tool"
    description = "Reading, querying, searching, creating, and editing Google Sheets data as a tool."
    icon = "Google"
    name = "GoogleSheetsTool"
    documentation = "https://docs.langflow.org/components-custom-components"

    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the Google Sheets action. Connect any component output here to trigger the action.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        FileInput(
            name="service_account_json",
            display_name="Service Account JSON File",
            file_types=["json"],
            info="Upload your Google Cloud Platform service account JSON key file.",
            required=True,
        ),
        StrInput(
            name="spreadsheet_id",
            display_name="Spreadsheet ID",
            info="The ID of the Google Spreadsheet (from the URL).",
            required=True,
        ),
        StrInput(
            name="worksheet_name",
            display_name="Worksheet Name",
            info="Name of the worksheet/tab to work with (default: first sheet).",
            advanced=True,
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="List of actions to perform with Google Sheets API.",
            options=[
                {"name": "Read All Data", "icon": "table"},
                {"name": "Search Data", "icon": "search"},
                {"name": "Query Data", "icon": "filter"},
                {"name": "Create Row", "icon": "plus"},
                {"name": "Update Row", "icon": "edit"},
                {"name": "Update Cell", "icon": "edit"},
                {"name": "Get Row Count", "icon": "hash"},
                {"name": "Get Column Headers", "icon": "columns"},
                {"name": "Test Connection", "icon": "wifi"}
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Search parameters
        MessageInput(
            name="search_column",
            display_name="Search Column",
            info="Column name or letter to search in (e.g., 'A', 'Name', 'Email').",
            show=False,
            tool_mode=True,
        ),
        MessageInput(
            name="search_value",
            display_name="Search Value",
            info="Value to search for in the specified column.",
            show=False,
            tool_mode=True,
        ),
        # Query parameters
        MessageInput(
            name="query",
            display_name="Filter Query",
            info="Expression to filter results. Example: 'column1 == \"value\"' or 'age > 25'.",
            show=False,
            tool_mode=True,
        ),
        # Row creation/update parameters
        DataInput(
            name="row_data",
            display_name="Row Data",
            info="Data for the new row or row to update (JSON format: {\"column\": \"value\"}).",
            show=False,
            tool_mode=True,
        ),
        MessageInput(
            name="row_number",
            display_name="Row Number",
            info="Row number to update (for Update Row action).",
            show=False,
            tool_mode=True,
        ),
        # Cell update parameters
        MessageInput(
            name="cell_address",
            display_name="Cell Address",
            info="Cell address to update (e.g., 'A1', 'B5').",
            show=False,
            tool_mode=True,
        ),
        MessageInput(
            name="cell_value",
            display_name="Cell Value",
            info="Value to set in the specified cell.",
            show=False,
            tool_mode=True,
        ),
        BoolInput(
            name="include_headers",
            display_name="Include Headers",
            info="Whether to include column headers in the output.",
            value=True,
            advanced=True,
        ),
        IntInput(
            name="max_rows",
            display_name="Max Rows",
            info="Maximum number of rows to return (0 for all).",
            value=100,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Result",
            method="execute_action"
        )
    ]

    def _get_service(self):
        """Initialize and return Google Sheets service."""
        if not hasattr(self, '_service') or self._service is None:
            # Check if dependencies are available
            if not globals().get('GOOGLE_SHEETS_AVAILABLE', False):
                raise ImportError("Google Sheets dependencies not available")
            
            if not self.service_account_json:
                raise ValueError("Service account JSON file is required")
            
            with open(self.service_account_json, "r", encoding="utf-8") as f:
                credentials_dict = json.load(f)
            
            # Use global service_account and build
            service_account_module = globals().get('service_account')
            build_module = globals().get('build')
            
            if not service_account_module or not build_module:
                raise ImportError("Google Sheets modules not available")
            
            credentials = service_account_module.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            
            self._service = build_module("sheets", "v4", credentials=credentials)
        
        return self._service

    def _get_range_name(self, range_suffix: str = "A:Z") -> str:
        """Get the full range name with worksheet prefix if specified."""
        if self.worksheet_name:
            return f"{self.worksheet_name}!{range_suffix}"
        return range_suffix

    def _get_sheet_name(self) -> str:
        """Get the actual sheet name (either specified or first sheet)."""
        if self.worksheet_name:
            return self.worksheet_name
        
        # Get the first sheet name from metadata
        service = self._get_service()
        spreadsheet_metadata = service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()
        first_sheet = spreadsheet_metadata.get("sheets", [{}])[0]
        return first_sheet.get("properties", {}).get("title", "Sheet1")

    def _get_headers(self) -> list:
        """Get column headers from the worksheet."""
        service = self._get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=self._get_range_name("1:1")
        ).execute()
        
        values = result.get("values", [])
        return values[0] if values else []

    def _get_data_as_dataframe(self) -> pd.DataFrame:
        """Get all data from worksheet as DataFrame."""
        service = self._get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=self._get_range_name()
        ).execute()
        
        values = result.get("values", [])
        
        if not values:
            return pd.DataFrame()
        
        if self.include_headers and len(values) > 1:
            headers = values[0]
            data_rows = values[1:]
            df = pd.DataFrame(data_rows, columns=headers)
        else:
            df = pd.DataFrame(values)
        
        if self.max_rows > 0:
            df = df.head(self.max_rows)
        
        return df

    def _parse_row_data(self, row_data: Any) -> Dict[str, Any]:
        """Parse row data from various input formats."""
        if isinstance(row_data, Data):
            return row_data.data
        elif isinstance(row_data, dict):
            return row_data
        elif isinstance(row_data, str):
            try:
                return json.loads(row_data)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for row data")
        else:
            raise ValueError("Row data must be a dictionary or JSON string")

    def _get_column_index(self, column: str, headers: list) -> int:
        """Get column index by name or letter."""
        if column.isdigit():
            return int(column) - 1
        
        if headers and column in headers:
            return headers.index(column)
        
        # Convert letter to index (A=0, B=1, etc.)
        column = column.upper()
        result = 0
        for char in column:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    def _extract_message_value(self, value: Any) -> str:
        """Extract string value from Message object or return as string."""
        if hasattr(value, 'content'):
            return str(value.content)
        elif hasattr(value, 'text'):
            return str(value.text)
        elif hasattr(value, 'message'):
            return str(value.message)
        elif isinstance(value, str):
            return value
        else:
            return str(value) if value is not None else ""

    def _make_json_serializable(self, data: Any) -> Any:
        """Convert data to JSON serializable format."""
        if isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif hasattr(data, 'item'):  # numpy types like int64, float64
            return data.item()
        elif hasattr(data, 'tolist'):  # numpy arrays
            return data.tolist()
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            return str(data)

    def read_all_data(self) -> Data:
        """Read all data from the worksheet."""
        try:
            df = self._get_data_as_dataframe()
            
            if df.empty:
                return Data(data={"message": "No data found in worksheet", "data": []})
            
            result_data = {
                "action": "Read All Data",
                "row_count": len(df),
                "data": df.to_dict('records')
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to read data: {str(e)}"})

    def search_data(self) -> Data:
        """Search for data in the worksheet."""
        try:
            search_column = self._extract_message_value(getattr(self, 'search_column', ''))
            search_value = self._extract_message_value(getattr(self, 'search_value', ''))
            
            if not search_column or not search_value:
                return Data(data={"error": "Search column and search value are required"})
            
            df = self._get_data_as_dataframe()
            
            if df.empty:
                result_data = {
                    "action": "Search Data",
                    "search_column": search_column,
                    "search_value": search_value,
                    "matches": 0,
                    "data": []
                }
                return Data(data=self._make_json_serializable(result_data))
            
            # Get headers for column lookup
            headers = self._get_headers()
            col_index = self._get_column_index(search_column, headers)
            
            # Search for matching values
            if col_index < len(df.columns):
                column_name = df.columns[col_index]
                matching_rows = df[df[column_name].astype(str).str.contains(
                    search_value, case=False, na=False
                )]
                
                # Add row numbers
                result_data = matching_rows.to_dict('records')
                for i, row in enumerate(result_data):
                    row["_row_number"] = matching_rows.index[i] + 2  # +2 for header row
                
                result_data_dict = {
                    "action": "Search Data",
                    "search_column": search_column,
                    "search_value": search_value,
                    "matches": len(result_data),
                    "data": result_data
                }
                return Data(data=self._make_json_serializable(result_data_dict))
            else:
                return Data(data={"error": f"Column '{search_column}' not found"})
            
        except Exception as e:
            return Data(data={"error": f"Failed to search data: {str(e)}"})

    def query_data(self) -> Data:
        """Query data using pandas query syntax."""
        try:
            query = self._extract_message_value(getattr(self, 'query', ''))
            
            if not query:
                return Data(data={"error": "Query expression is required for Query Data action"})
            
            df = self._get_data_as_dataframe()
            
            if df.empty:
                return Data(data={"message": "No data found in worksheet", "data": []})
            
            try:
                filtered_df = df.query(query, engine="python")
            except Exception as query_error:
                return Data(data={"error": f"Query error: {str(query_error)}"})
            
            result_data = {
                "action": "Query Data",
                "query": query,
                "row_count": len(filtered_df),
                "data": filtered_df.to_dict('records')
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to query data: {str(e)}"})

    def create_row(self) -> Data:
        """Create a new row in the worksheet."""
        try:
            if not self.row_data:
                return Data(data={"error": "Row data is required for creating a row"})
            
            service = self._get_service()
            row_dict = self._parse_row_data(self.row_data)
            headers = self._get_headers()
            
            # Prepare row data in the correct order
            row_values = [str(row_dict.get(header, "")) for header in headers]
            
            # Add the row
            service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=self._get_sheet_name(),
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_values]}
            ).execute()
            
            # Get new row count
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=self._get_range_name()
            ).execute()
            new_row_number = len(result.get("values", []))
            
            result_data = {
                "action": "Create Row",
                "row_number": new_row_number,
                "data": row_dict,
                "message": f"Successfully created row {new_row_number}"
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to create row: {str(e)}"})

    def update_row(self) -> Data:
        """Update an existing row in the worksheet."""
        try:
            row_data = getattr(self, 'row_data', None)
            row_number = self._extract_message_value(getattr(self, 'row_number', ''))
            
            if not row_data or not row_number:
                return Data(data={"error": "Row data and row number are required for updating a row"})
            
            service = self._get_service()
            row_dict = self._parse_row_data(row_data)
            headers = self._get_headers()
            
            # Prepare row data in the correct order
            row_values = [str(row_dict.get(header, "")) for header in headers]
            
            # Update the row
            update_range = f"{self._get_sheet_name()}!{row_number}:{row_number}"
            service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=update_range,
                valueInputOption="RAW",
                body={"values": [row_values]}
            ).execute()
            
            result_data = {
                "action": "Update Row",
                "row_number": row_number,
                "data": row_dict,
                "message": f"Successfully updated row {row_number}"
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to update row: {str(e)}"})

    def update_cell(self) -> Data:
        """Update a specific cell in the worksheet."""
        try:
            cell_address = self._extract_message_value(getattr(self, 'cell_address', ''))
            cell_value = self._extract_message_value(getattr(self, 'cell_value', ''))
            
            if not cell_address or not cell_value:
                return Data(data={"error": "Cell address and cell value are required for updating a cell"})
            
            service = self._get_service()
            
            # Determine the range to update
            if self.worksheet_name:
                range_name = f"{self.worksheet_name}!{cell_address}"
            else:
                range_name = cell_address
            
            # Update the cell
            service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [[cell_value]]}
            ).execute()
            
            result_data = {
                "action": "Update Cell",
                "cell_address": cell_address,
                "cell_value": cell_value,
                "message": f"Successfully updated cell {cell_address} with value '{cell_value}'"
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to update cell: {str(e)}"})

    def get_row_count(self) -> Data:
        """Get the number of rows in the worksheet."""
        try:
            df = self._get_data_as_dataframe()
            row_count = len(df)
            
            result_data = {
                "action": "Get Row Count",
                "row_count": row_count,
                "message": f"Worksheet has {row_count} rows"
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to get row count: {str(e)}"})

    def get_column_headers(self) -> Data:
        """Get the column headers of the worksheet."""
        try:
            headers = self._get_headers()
            
            result_data = {
                "action": "Get Column Headers",
                "headers": headers,
                "column_count": len(headers),
                "message": f"Found {len(headers)} columns"
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Failed to get column headers: {str(e)}"})

    def test_connection(self) -> Data:
        """Test connection to Google Sheets and provide detailed information."""
        try:
            service = self._get_service()
            
            if not self.spreadsheet_id:
                return Data(data={"error": "Spreadsheet ID is required"})
            
            # Get spreadsheet metadata
            spreadsheet_metadata = service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            spreadsheet_info = {
                "title": spreadsheet_metadata.get("properties", {}).get("title", "Unknown"),
                "id": spreadsheet_metadata.get("spreadsheetId", self.spreadsheet_id),
                "url": f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
            }
            
            # List available worksheets
            sheets = spreadsheet_metadata.get("sheets", [])
            worksheet_info = []
            for sheet in sheets:
                properties = sheet.get("properties", {})
                worksheet_info.append({
                    "title": properties.get("title", "Unknown"),
                    "id": properties.get("sheetId", "Unknown"),
                    "row_count": properties.get("gridProperties", {}).get("rowCount", 0),
                    "col_count": properties.get("gridProperties", {}).get("columnCount", 0)
                })
            
            # Test reading data
            try:
                df = self._get_data_as_dataframe()
                data_info = {
                    "total_rows": len(df),
                    "sample_rows": df.head(3).to_dict('records') if not df.empty else [],
                    "has_headers": not df.empty
                }
            except Exception as e:
                data_info = f"Could not read data: {str(e)}"
            
            result_data = {
                "action": "Test Connection",
                "status": "success",
                "spreadsheet_info": spreadsheet_info,
                "worksheet_info": worksheet_info,
                "data_info": data_info,
                "message": "Connection successful! You can now use other actions."
            }
            return Data(data=self._make_json_serializable(result_data))
            
        except Exception as e:
            return Data(data={"error": f"Connection test failed: {str(e)}"})


    def execute_action(self) -> Data:
        """Execute the selected action."""
        try:
            # Check dependencies - try to import again at runtime
            if not GOOGLE_SHEETS_AVAILABLE:
                try:
                    from google.oauth2 import service_account
                    from googleapiclient.discovery import build
                    # If successful, update global variables
                    globals()['GOOGLE_SHEETS_AVAILABLE'] = True
                    globals()['service_account'] = service_account
                    globals()['build'] = build
                except ImportError as runtime_error:
                    return Data(data={
                        "error": "Google Sheets dependencies not available. Please install required packages:",
                        "installation_commands": [
                            "pip install google-auth",
                            "pip install google-api-python-client"
                        ],
                        "note": "You can also use the 'Libraries Install' component to install these dependencies.",
                        "requirements": "Upload your Google Service Account JSON key file to use this component.",
                        "debug_info": {
                            "import_error": str(runtime_error),
                            "service_account_available": globals().get('service_account') is not None,
                            "build_available": globals().get('build') is not None
                        }
                    })
            
            # Reset service to handle different spreadsheets
            if hasattr(self, '_service'):
                self._service = None
            
            # Extract action name from the selected action (like Pipefy)
            action_name = None
            if isinstance(self.action, list) and len(self.action) > 0:
                action_name = self.action[0].get("name")
            elif isinstance(self.action, dict):
                action_name = self.action.get("name")
            
            if not action_name:
                return Data(data={"error": "Invalid action selected"})

            # Execute action
            action_map = {
                "Read All Data": self.read_all_data,
                "Search Data": self.search_data,
                "Query Data": self.query_data,
                "Create Row": self.create_row,
                "Update Row": self.update_row,
                "Update Cell": self.update_cell,
                "Get Row Count": self.get_row_count,
                "Get Column Headers": self.get_column_headers,
                "Test Connection": self.test_connection
            }
            
            if action_name in action_map:
                return action_map[action_name]()
            else:
                return Data(data={"error": f"Unknown action: {action_name}"})
                
        except Exception as e:
            return Data(data={"error": f"Action execution failed: {str(e)}"})

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        """Update build configuration based on selected action."""
        if field_name != "action":
            return build_config

        # Extract action name from the selected action (like Pipefy)
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Search Data": ["search_column", "search_value"],
            "Query Data": ["query"],
            "Create Row": ["row_data"],
            "Update Row": ["row_data", "row_number"],
            "Update Cell": ["cell_address", "cell_value"]
        }

        # Hide all action-specific fields first
        for field_name in ["search_column", "search_value", "query", "row_data", "row_number", "cell_address", "cell_value"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config