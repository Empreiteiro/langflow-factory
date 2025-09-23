import json
from typing import Any

import requests
from pydantic import BaseModel, Field

from lfx.custom import Component
from lfx.io import MultilineInput, SecretStrInput, StrInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class NotionListPages(Component):
    display_name: str = "List Pages "
    description: str = (
        "Query a Notion database with filtering and sorting. "
        "The input should be a JSON string containing the 'filter' and 'sorts' objects. "
        "Example input:\n"
        '{"filter": {"property": "Status", "select": {"equals": "Done"}}, '
        '"sorts": [{"timestamp": "created_time", "direction": "descending"}]}'
    )
    documentation: str = "https://docs.langflow.org/integrations/notion/list-pages"
    icon = "NotionDirectoryLoader"

    inputs = [
        SecretStrInput(
            name="notion_secret",
            display_name="Notion Secret",
            info="The Notion integration token.",
            required=True,
        ),
        StrInput(
            name="database_id",
            display_name="Database ID",
            info="The ID of the Notion database to query. You can find this in the database URL: notion.so/[workspace]/[database_id]?v=...",
            required=True,
        ),
        MultilineInput(
            name="query_json",
            display_name="Database query (JSON)",
            info="A JSON string containing the filters and sorts that will be used for querying the database. "
            "Leave empty for no filters or sorts.",
        ),
    ]

    outputs = [
        Output(
            name="dataframe",
            display_name="DataFrame",
            method="build_dataframe",
            info="The resulting DataFrame with pages data.",
        ),
        Output(
            name="data",
            display_name="Data",
            method="build_data",
            info="Individual page data objects (for Page Content component).",
        ),
    ]

    def build_dataframe(self) -> DataFrame:
        """Build DataFrame output from Notion pages."""
        # Validate required inputs
        if not self.database_id or not self.database_id.strip():
            error_df = [{"error": "Database ID is required", "id": "", "url": "", "created_time": "", "last_edited_time": "", "properties": ""}]
            return DataFrame(error_df)
        
        if not self.notion_secret or not self.notion_secret.strip():
            error_df = [{"error": "Notion Secret is required", "id": "", "url": "", "created_time": "", "last_edited_time": "", "properties": ""}]
            return DataFrame(error_df)

        result = self._query_notion_database(self.database_id, self.query_json)

        if isinstance(result, str):
            # An error occurred, return empty DataFrame with error info
            error_df = [{"error": result, "id": "", "url": "", "created_time": "", "last_edited_time": "", "properties": ""}]
            return DataFrame(error_df)

        # Convert pages to DataFrame format
        pages_data = []
        for page in result:
            page_data = {
                "id": page["id"],
                "url": page["url"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
                "properties": json.dumps(page["properties"], indent=2)
            }
            pages_data.append(page_data)

        if not pages_data:
            # Return empty DataFrame with proper columns
            empty_df = [{"id": "", "url": "", "created_time": "", "last_edited_time": "", "properties": ""}]
            return DataFrame(empty_df)

        return DataFrame(pages_data)

    def build_data(self) -> list[Data]:
        """Build Data objects output for compatibility with Page Content component."""
        # Validate required inputs
        if not self.notion_secret or not self.notion_secret.strip():
            return [Data(text="Notion Secret is required")]
        
        if not self.database_id or not self.database_id.strip():
            return [Data(text="Database ID is required")]

        result = self._query_notion_database(self.database_id, self.query_json)

        if isinstance(result, str):
            # An error occurred, return it as a single record
            return [Data(text=result)]

        records = []
        for page in result:
            page_data = {
                "id": page["id"],
                "url": page["url"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
                "properties": page["properties"],
            }

            text = (
                f"id: {page['id']}\n"
                f"url: {page['url']}\n"
                f"created_time: {page['created_time']}\n"
                f"last_edited_time: {page['last_edited_time']}\n"
                f"properties: {json.dumps(page['properties'], indent=2)}\n\n"
            )

            records.append(Data(text=text, data=page_data))

        return records

    def _query_notion_database(self, database_id: str, query_json: str | None = None) -> list[dict[str, Any]] | str:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        query_payload = {}
        if query_json and query_json.strip():
            try:
                query_payload = json.loads(query_json)
            except json.JSONDecodeError as e:
                return f"Invalid JSON format for query: {e}"

        try:
            response = requests.post(url, headers=headers, json=query_payload, timeout=10)
            response.raise_for_status()
            results = response.json()
            return results["results"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                try:
                    error_details = response.json()
                    error_msg = error_details.get("message", "Bad Request")
                    return f"Notion API Error (400): {error_msg}. Please check your Database ID and ensure the integration has access to the database."
                except:
                    return f"Notion API Error (400): Bad Request. Please verify your Database ID is correct and the integration has access to the database."
            elif response.status_code == 401:
                return "Notion API Error (401): Unauthorized. Please check your Notion Secret token."
            elif response.status_code == 404:
                return "Notion API Error (404): Database not found. Please verify the Database ID is correct and the integration has access to it."
            else:
                return f"Notion API Error ({response.status_code}): {e}"
        except requests.exceptions.RequestException as e:
            return f"Network error querying Notion database: {e}"
        except KeyError:
            return "Unexpected response format from Notion API"
        except Exception as e:  # noqa: BLE001
            return f"An unexpected error occurred: {e}"
