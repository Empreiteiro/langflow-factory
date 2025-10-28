"""
MCP Context Forge List Prompts Component

This component lists all available prompts in the MCP Context Forge server
by making a curl request to the /prompts endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ListPromptsComponent(Component):
    display_name = "MCP List Prompts"
    description = "List all available prompts in the MCP Context Forge server"
    icon = "message-square"
    name = "ListPromptsComponent"
    
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
    ]
    
    outputs = [
        Output(name="prompts_list", display_name="Prompts List", method="list_prompts"),
    ]
    
    def list_prompts(self) -> Data:
        """
        List all available prompts in the MCP Context Forge server.
        
        Returns:
            Data: Contains the list of available prompts
        """
        base_url = self.base_url.rstrip('/')
        prompts_url = f"{base_url}/prompts"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to list prompts
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                prompts_url
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
                        "url": prompts_url
                    }
                )
            
            # Try to parse JSON response
            try:
                prompts_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": prompts_data,
                        "url": prompts_url,
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
                        "url": prompts_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": prompts_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": prompts_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": prompts_url
                }
            )
