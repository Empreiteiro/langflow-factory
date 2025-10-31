"""
MCP Context Forge List Tags Component

This component lists all available tags in the MCP Context Forge server
by making a curl request to the /tags endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, BoolInput
from lfx.schema import Data


class ListTagsComponent(Component):
    display_name = "MCP List Tags"
    description = "List all available tags in the MCP Context Forge server"
    icon = "tag"
    name = "ListTagsComponent"
    
    inputs = [
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="The base URL of the MCP Context Forge server (e.g., http://localhost:4444)",
            value="http://localhost:4444",
        ),
        SecretStrInput(
            name="token",
            display_name="Bearer Token",
            info="The Bearer token for authentication",
            required=True,
        ),
        StrInput(
            name="entity_types",
            display_name="Entity Types",
            info="Comma-separated entity types to filter (e.g., gateways,servers,tools,resources,prompts)",
            value="gateways,servers,tools,resources,prompts",
            required=False,
        ),
        BoolInput(
            name="include_entities",
            display_name="Include Entities",
            info="Whether to include entity details in the response",
            value=False,
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="tags_list", display_name="Tags List", method="list_tags"),
    ]
    
    def list_tags(self) -> Data:
        """
        List all available tags in the MCP Context Forge server.
        
        Returns:
            Data: Contains the list of available tags
        """
        base_url = self.base_url.rstrip('/')
        
        # Build query parameters
        params = []
        if self.entity_types:
            params.append(f"entity_types={self.entity_types}")
        if hasattr(self, 'include_entities') and self.include_entities is not None:
            params.append(f"include_entities={str(self.include_entities).lower()}")
        
        query_string = "&".join(params)
        tags_url = f"{base_url}/tags"
        if query_string:
            tags_url += f"?{query_string}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to list tags
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                tags_url
            ]
            
            # Run the curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "url": tags_url
                    }
                )
            
            # Try to parse JSON response
            try:
                tags_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": tags_data,
                        "url": tags_url,
                        "raw_response": result.stdout
                    }
                )
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response
                return Data(
                    value={
                        "status": "success",
                        "message": "Server responded but response is not valid JSON",
                        "raw_response": result.stdout,
                        "url": tags_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": tags_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": tags_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": tags_url
                }
            )
