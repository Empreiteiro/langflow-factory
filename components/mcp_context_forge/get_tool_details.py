"""
MCP Context Forge Get Tool Details Component

This component retrieves details of a specific tool by ID from the MCP Context Forge server
by making a curl request to the /tools/{tool_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetToolDetailsComponent(Component):
    display_name = "MCP Get Tool Details"
    description = "Get details of a specific tool by ID from the MCP Context Forge server"
    icon = "info"
    name = "GetToolDetailsComponent"
    
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
            name="tool_id",
            display_name="Tool ID",
            info="The ID of the tool to retrieve details for",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="tool_details", display_name="Tool Details", method="get_tool_details"),
    ]
    
    def get_tool_details(self) -> Data:
        """
        Get details of a specific tool by ID from the MCP Context Forge server.
        
        Returns:
            Data: Contains the tool details including input/output schemas
        """
        base_url = self.base_url.rstrip('/')
        tool_url = f"{base_url}/tools/{self.tool_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get tool details
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                tool_url
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
                        "url": tool_url,
                        "tool_id": self.tool_id
                    }
                )
            
            # Try to parse JSON response
            try:
                tool_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": tool_data,
                        "url": tool_url,
                        "tool_id": self.tool_id,
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
                        "url": tool_url,
                        "tool_id": self.tool_id
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": tool_url,
                    "tool_id": self.tool_id
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": tool_url,
                    "tool_id": self.tool_id
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": tool_url,
                    "tool_id": self.tool_id
                }
            )
