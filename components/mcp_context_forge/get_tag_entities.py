"""
MCP Context Forge Get Tag Entities Component

This component retrieves entities associated with a specific tag from the MCP Context Forge server
by making a curl request to the /tags/{tag_name}/entities endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetTagEntitiesComponent(Component):
    display_name = "MCP Get Tag Entities"
    description = "Get entities associated with a specific tag from the MCP Context Forge server"
    icon = "list"
    name = "GetTagEntitiesComponent"
    
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
            name="tag_name",
            display_name="Tag Name",
            info="The name of the tag to get entities for",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="tag_entities", display_name="Tag Entities", method="get_tag_entities"),
    ]
    
    def get_tag_entities(self) -> Data:
        """
        Get entities associated with a specific tag from the MCP Context Forge server.
        
        Returns:
            Data: Contains the entities associated with the tag
        """
        base_url = self.base_url.rstrip('/')
        tag_entities_url = f"{base_url}/tags/{self.tag_name}/entities"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get tag entities
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                tag_entities_url
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
                        "url": tag_entities_url,
                        "tag_name": self.tag_name
                    }
                )
            
            # Try to parse JSON response
            try:
                entities_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": entities_data,
                        "url": tag_entities_url,
                        "tag_name": self.tag_name,
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
                        "url": tag_entities_url,
                        "tag_name": self.tag_name
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": tag_entities_url,
                    "tag_name": self.tag_name
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": tag_entities_url,
                    "tag_name": self.tag_name
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": tag_entities_url,
                    "tag_name": self.tag_name
                }
            )
