from typing import Any

import requests
from pydantic import BaseModel, Field

from lfx.custom import Component
from lfx.io import DropdownInput, SecretStrInput, StrInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class NotionSearch(Component):
    display_name: str = "Search "
    description: str = "Searches all pages and databases that have been shared with an integration."
    documentation: str = "https://docs.langflow.org/integrations/notion/search"
    icon = "NotionDirectoryLoader"

    inputs = [
        SecretStrInput(
            name="notion_secret",
            display_name="Notion Secret",
            info="The Notion integration token.",
            required=True,
        ),
        StrInput(
            name="query",
            display_name="Search Query",
            info="The text that the API compares page and database titles against. Leave empty to search all pages/databases.",
        ),
        DropdownInput(
            name="filter_value",
            display_name="Filter Type",
            info="Limits the results to either only pages or only databases.",
            options=["page", "database"],
            value="page",
        ),
        DropdownInput(
            name="sort_direction",
            display_name="Sort Direction",
            info="The direction to sort the results.",
            options=["ascending", "descending"],
            value="descending",
        ),
    ]

    outputs = [
        Output(
            name="dataframe",
            display_name="DataFrame",
            method="build_dataframe",
            info="The search results as a DataFrame.",
        ),
        Output(
            name="data",
            display_name="Data",
            method="build_data",
            info="Individual page data objects (for Page Content component).",
        ),
    ]

    def build_dataframe(self) -> DataFrame:
        """Build DataFrame output from Notion search results."""
        # Validate required inputs
        if not self.notion_secret or not self.notion_secret.strip():
            error_df = [{"error": "Notion Secret is required", "id": "", "type": "", "title_or_url": "", "last_edited_time": ""}]
            return DataFrame(error_df)

        result = self._search_notion(self.query, self.filter_value, self.sort_direction)

        if isinstance(result, str):
            # An error occurred, return empty DataFrame with error info
            error_df = [{"error": result, "id": "", "type": "", "title_or_url": "", "last_edited_time": ""}]
            return DataFrame(error_df)

        # Convert search results to DataFrame format
        results_data = []
        for result_item in result:
            result_data = {
                "id": result_item["id"],
                "type": result_item["object"],
                "last_edited_time": result_item["last_edited_time"],
            }

            if result_item["object"] == "page":
                result_data["title_or_url"] = result_item["url"]
            elif result_item["object"] == "database":
                if "title" in result_item and isinstance(result_item["title"], list) and len(result_item["title"]) > 0:
                    result_data["title_or_url"] = result_item["title"][0]["plain_text"]
                else:
                    result_data["title_or_url"] = "N/A"

            results_data.append(result_data)

        if not results_data:
            # Return empty DataFrame with proper columns
            empty_df = [{"id": "", "type": "", "title_or_url": "", "last_edited_time": ""}]
            return DataFrame(empty_df)

        return DataFrame(results_data)

    def build_data(self) -> Data:
        """Build simplified Data output with array of page IDs for Page Content component."""
        # Validate required inputs
        if not self.notion_secret or not self.notion_secret.strip():
            return Data(text="Notion Secret is required")

        result = self._search_notion(self.query, self.filter_value, self.sort_direction)

        if isinstance(result, str):
            # An error occurred, return it as a single record
            return Data(text=result)

        # Extract only page IDs (not databases)
        page_ids = []
        for result_item in result:
            if result_item["object"] == "page":
                page_ids.append(result_item["id"])

        if not page_ids:
            if self.filter_value == "database":
                return Data(text="No pages found - filter is set to 'database'. Change filter to 'page' to find pages.")
            else:
                return Data(text="No pages found in search results")

        # Create simplified JSON with array of IDs
        data_payload = {
            "ids": page_ids,
            "count": len(page_ids),
            "type": "page_ids"
        }
        
        text_content = f"Found {len(page_ids)} pages:\n" + "\n".join(page_ids)

        return Data(text=text_content, data=data_payload)

    def _search_notion(
        self, query: str, filter_value: str = "page", sort_direction: str = "descending"
    ) -> list[dict[str, Any]] | str:
        url = "https://api.notion.com/v1/search"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        data = {
            "filter": {"value": filter_value, "property": "object"},
            "sort": {"direction": sort_direction, "timestamp": "last_edited_time"},
        }
        
        # Only add query to request if it's provided
        if query and query.strip():
            data["query"] = query

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            results = response.json()
            return results["results"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                try:
                    error_details = response.json()
                    error_msg = error_details.get("message", "Bad Request")
                    return f"Notion API Error (400): {error_msg}. Please check your search parameters."
                except:
                    return f"Notion API Error (400): Bad Request. Please verify your search parameters are correct."
            elif response.status_code == 401:
                return "Notion API Error (401): Unauthorized. Please check your Notion Secret token."
            else:
                return f"Notion API Error ({response.status_code}): {e}"
        except requests.exceptions.RequestException as e:
            return f"Network error querying Notion: {e}"
        except KeyError:
            return "Unexpected response format from Notion API"
        except Exception as e:  # noqa: BLE001
            return f"An unexpected error occurred: {e}"
