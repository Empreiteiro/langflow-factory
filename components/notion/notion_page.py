import re
import requests
from pydantic import BaseModel, Field

from langflow.custom import Component
from langflow.io import SecretStrInput, MessageTextInput, Output, DataInput
from langflow.schema.data import Data
from langflow.schema.dataframe import DataFrame


class NotionPageContent(Component):
    display_name = "Page Content Viewer "
    description = "Retrieve the content of a Notion page as plain text."
    documentation = "https://docs.langflow.org/integrations/notion/page-content-viewer"
    icon = "NotionDirectoryLoader"

    inputs = [
        DataInput(
            name="page_data",
            display_name="Page Data",
            info="Data containing the page ID (from Notion Search/List Pages).",
            required=False,
        ),
        MessageTextInput(
            name="page_id",
            display_name="Page ID",
            info="The ID of the Notion page to retrieve. Can be UUID or URL.",
            required=False,
        ),
        SecretStrInput(
            name="notion_secret",
            display_name="Notion Secret",
            info="The Notion integration token.",
            required=True,
        ),
    ]

    outputs = [
        Output(
            name="dataframe",
            display_name="DataFrame",
            method="build_dataframe",
            info="The page content as a DataFrame.",
        ),
        Output(
            name="data",
            display_name="Data",
            method="build_data",
            info="The page content as Data object.",
        ),
    ]

    def extract_page_ids(self) -> list[str]:
        """Extract page IDs from various input sources."""
        page_ids = []
        
        # Try to get from page_data first (from other Notion components)
        if self.page_data:
            if hasattr(self.page_data, 'data') and self.page_data.data:
                # Check if it's the new simplified format with array of IDs
                if self.page_data.data.get('type') == 'page_ids' and 'ids' in self.page_data.data:
                    ids_array = self.page_data.data.get('ids', [])
                    if ids_array:
                        page_ids = ids_array  # Take all page IDs
                # Check for single page format
                elif 'id' in self.page_data.data:
                    page_ids = [self.page_data.data.get('id', '')]
            elif hasattr(self.page_data, 'text') and self.page_data.text:
                # Extract UUID from text if it contains one
                uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                matches = re.findall(uuid_pattern, self.page_data.text)
                if matches:
                    page_ids = matches
        
        # If not found, try direct page_id input
        if not page_ids and self.page_id:
            page_ids = [self.page_id]
        
        return page_ids

    def build_dataframe(self) -> DataFrame:
        """Build DataFrame output from Notion page content."""
        # Validate required inputs
        if not self.notion_secret or not self.notion_secret.strip():
            error_df = [{"error": "Notion Secret is required", "page_id": "", "content": "", "title": ""}]
            return DataFrame(error_df)
        
        page_ids = self.extract_page_ids()
        if not page_ids:
            error_df = [{"error": "Page ID is required (from Page Data or Page ID input)", "page_id": "", "content": "", "title": ""}]
            return DataFrame(error_df)
        
        # Process all page IDs
        content_data = []
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        for page_id in page_ids:
            # Clean up page_id (remove URL parts if present)
            if page_id:
                # Extract UUID from Notion URL if full URL is provided
                uuid_match_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                match = re.search(uuid_match_pattern, page_id)
                if match:
                    page_id = match.group()
                
                # Remove hyphens and add them back in correct format
                clean_id = re.sub(r'[^0-9a-f]', '', page_id.lower())
                if len(clean_id) == 32:
                    page_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
            
            # Validate UUID format
            if not re.match(uuid_pattern, page_id):
                content_data.append({
                    "page_id": page_id,
                    "title": "Error", 
                    "content": f"Invalid page ID format: {page_id}",
                    "content_length": 0
                })
                continue

            # Retrieve content for this page
            result = self._retrieve_page_content(page_id)

            if isinstance(result, str) and result.startswith("Error:"):
                content_data.append({
                    "page_id": page_id,
                    "title": "Error",
                    "content": result,
                    "content_length": 0
                })
                continue

            # Get page title
            page_title = self._get_page_title(page_id)

            # Add page data
            content_data.append({
                "page_id": page_id,
                "title": page_title,
                "content": result,
                "content_length": len(result)
            })

        if not content_data:
            error_df = [{"error": "No valid pages found", "page_id": "", "content": "", "title": ""}]
            return DataFrame(error_df)

        return DataFrame(content_data)

    def build_data(self) -> Data:
        """Build Data output from Notion page content."""
        page_ids = self.extract_page_ids()
        if not page_ids:
            return Data(text="Error: Page ID is required")
        
        # If multiple pages, return first one for Data format
        page_id = page_ids[0]
        
        # Clean up page_id
        if page_id:
            uuid_match_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            match = re.search(uuid_match_pattern, page_id)
            if match:
                page_id = match.group()
            
            clean_id = re.sub(r'[^0-9a-f]', '', page_id.lower())
            if len(clean_id) == 32:
                page_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        
        result = self._retrieve_page_content(page_id)
        if isinstance(result, str) and result.startswith("Error:"):
            return Data(text=result)
        
        # Get page title
        page_title = self._get_page_title(page_id)
        
        return Data(
            text=result, 
            data={
                "content": result, 
                "page_id": page_id,
                "title": page_title
            }
        )

    def _get_page_title(self, page_id: str) -> str:
        """Get the title of a Notion page."""
        page_url = f"https://api.notion.com/v1/pages/{page_id}"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Notion-Version": "2022-06-28",
        }
        
        try:
            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()
            page_data = response.json()
            
            # Extract title from properties
            properties = page_data.get("properties", {})
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_list = prop_data.get("title", [])
                    if title_list:
                        return "".join(segment.get("plain_text", "") for segment in title_list)
            
            return "Untitled"
        except Exception:
            return "Unknown"

    def _retrieve_page_content(self, page_id: str) -> str:
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Notion-Version": "2022-06-28",
        }
        try:
            blocks_response = requests.get(blocks_url, headers=headers, timeout=10)
            blocks_response.raise_for_status()
            blocks_data = blocks_response.json()
            return self.parse_blocks(blocks_data.get("results", []))
        except requests.exceptions.HTTPError as e:
            if blocks_response.status_code == 400:
                try:
                    error_details = blocks_response.json()
                    error_msg = error_details.get("message", "Bad Request")
                    return f"Error: Notion API (400): {error_msg}. Please verify the page ID is correct."
                except:
                    return f"Error: Bad Request (400). Please verify the page ID format is correct."
            elif blocks_response.status_code == 401:
                return "Error: Unauthorized (401). Please check your Notion Secret token."
            elif blocks_response.status_code == 404:
                return "Error: Page not found (404). Please verify the page ID and integration access."
            else:
                return f"Error: Notion API ({blocks_response.status_code}): {e}"
        except requests.exceptions.RequestException as e:
            return f"Error: Network error retrieving page content: {e}"
        except Exception as e:  # noqa: BLE001
            return f"Error: An unexpected error occurred while retrieving Notion page content: {e}"

    def parse_blocks(self, blocks: list) -> str:
        content = ""
        for block in blocks:
            block_type = block.get("type")
            if block_type in {"paragraph", "heading_1", "heading_2", "heading_3", "quote"}:
                content += self.parse_rich_text(block[block_type].get("rich_text", [])) + "\n\n"
            elif block_type in {"bulleted_list_item", "numbered_list_item"}:
                content += self.parse_rich_text(block[block_type].get("rich_text", [])) + "\n"
            elif block_type == "to_do":
                content += self.parse_rich_text(block["to_do"].get("rich_text", [])) + "\n"
            elif block_type == "code":
                content += self.parse_rich_text(block["code"].get("rich_text", [])) + "\n\n"
            elif block_type == "image":
                content += f"[Image: {block['image'].get('external', {}).get('url', 'No URL')}]\n\n"
            elif block_type == "divider":
                content += "---\n\n"
        return content.strip()

    def parse_rich_text(self, rich_text: list) -> str:
        return "".join(segment.get("plain_text", "") for segment in rich_text)
