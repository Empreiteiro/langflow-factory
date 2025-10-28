"""
MCP Context Forge Toggle Tool Component

This component toggles the enabled status of a tool in the MCP Context Forge server
by making a POST request to the /tools/{tool_id}/toggle endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, BoolInput
from lfx.schema import Data


class ToggleToolComponent(Component):
    display_name = "MCP Toggle Tool"
    description = "Toggle the enabled status of a tool in the MCP Context Forge server"
    icon = "toggle-right"
    name = "ToggleToolComponent"
    
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
            info="The ID of the tool to toggle",
            required=True,
        ),
        BoolInput(
            name="activate",
            display_name="Activate",
            info="Whether to activate (true) or deactivate (false) the tool",
            value=True,
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="toggle_result", display_name="Toggle Result", method="toggle_tool"),
    ]
    
    def toggle_tool(self) -> Data:
        """
        Toggle the enabled status of a tool in the MCP Context Forge server.
        
        Returns:
            Data: Contains the toggle result
        """
        base_url = self.base_url.rstrip('/')
        tool_url = f"{base_url}/tools/{self.tool_id}/toggle"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare query parameter
        activate_param = "true" if self.activate else "false"
        toggle_url = f"{tool_url}?activate={activate_param}"
        
        try:
            # Execute curl command to toggle tool
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                toggle_url
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
                        "url": toggle_url,
                        "tool_id": self.tool_id,
                        "activate": self.activate
                    }
                )
            
            # Try to parse JSON response
            try:
                toggle_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": toggle_data,
                        "url": toggle_url,
                        "tool_id": self.tool_id,
                        "activate": self.activate,
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
                        "url": toggle_url,
                        "tool_id": self.tool_id,
                        "activate": self.activate
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": toggle_url,
                    "tool_id": self.tool_id,
                    "activate": self.activate
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": toggle_url,
                    "tool_id": self.tool_id,
                    "activate": self.activate
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": toggle_url,
                    "tool_id": self.tool_id,
                    "activate": self.activate
                }
            )
