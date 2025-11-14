from langflow.custom import Component
from langflow.io import (
    SecretStrInput,
    DropdownInput,
    IntInput,
    StrInput,
    TabInput,
    Output,
)
from langflow.schema import Data
import requests
import json
from typing import Any, Optional


class GammaListComponent(Component):
    display_name = "Gamma List Themes/Folders"
    description = "Lists themes or folders from Gamma API using /v1.0/themes or /v1.0/folders endpoints."
    icon = "custom"
    name = "GammaListComponent"
    beta = False

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Gamma API key (X-API-KEY header)."
        ),
        TabInput(
            name="resource_type",
            display_name="Resource Type",
            info="Select whether to list themes or folders.",
            options=["Themes", "Folders"],
            value="Themes",
            real_time_refresh=True,
        ),
        StrInput(
            name="query",
            display_name="Query",
            required=False,
            info="Search by name (case-insensitive). Filters results to items matching the search term.",
            advanced=True,
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            required=False,
            info="Number of items to return per page. Maximum: 50.",
            value=50,
            advanced=True,
        ),
        StrInput(
            name="after",
            display_name="After (Cursor)",
            required=False,
            info="Cursor token for fetching the next page. Use the nextCursor value from the previous response.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Result",
            method="list_output",
        )
    ]

    field_order = [
        "api_key",
        "resource_type",
        "query",
        "limit",
        "after",
    ]

    def build(self):
        """Executes the Gamma API call and saves the result in state."""
        resource_type = getattr(self, "resource_type", "Themes")
        
        # Determine endpoint based on resource type
        if resource_type == "Folders":
            url = "https://public-api.gamma.app/v1.0/folders"
        else:
            url = "https://public-api.gamma.app/v1.0/themes"

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        # Build query parameters
        params: dict[str, Any] = {}

        if hasattr(self, "query") and self.query:
            params["query"] = self.query

        if hasattr(self, "limit") and self.limit:
            # Ensure limit is within valid range (1-50)
            limit_value = max(1, min(50, int(self.limit)))
            params["limit"] = limit_value

        if hasattr(self, "after") and self.after:
            params["after"] = self.after

        try:
            self.log(f"Fetching {resource_type.lower()} from Gamma API: {url}")
            self.log(f"Query parameters: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.status_code != 200:
                msg = f"Gamma API error ({response.status_code}): {response.text}"
                self.status = msg
                self.update_state("gamma_list_result", {"error": msg})
                return

            data = response.json()
            self.update_state("gamma_list_result", data)
            self.status = f"Successfully fetched {resource_type.lower()}."

        except Exception as e:
            msg = f"Error calling Gamma API: {e!s}"
            self.status = msg
            self.update_state("gamma_list_result", {"error": msg})
            self.log(msg)

    def list_output(self) -> Data:
        """Returns the result stored in state."""
        result = self.get_state("gamma_list_result")

        if not result:
            return Data(data={"error": "No result found."})

        return Data(data=result)

