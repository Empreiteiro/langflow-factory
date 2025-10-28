"""
MCP Context Forge Get Virtual Server Details Component

This component retrieves details of a specific virtual server by ID from the MCP Context Forge server
by making a curl request to the /servers/{server_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetVirtualServerDetailsComponent(Component):
    display_name = "MCP Get Virtual Server Details"
    description = "Get details of a specific virtual server by ID from the MCP Context Forge server"
    icon = "info"
    name = "GetVirtualServerDetailsComponent"
    
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
            name="server_id",
            display_name="Server ID",
            info="The ID of the virtual server to retrieve details for",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="server_details", display_name="Server Details", method="get_server_details"),
    ]
    
    def get_server_details(self) -> Data:
        """
        Get details of a specific virtual server by ID from the MCP Context Forge server.
        
        Returns:
            Data: Contains the virtual server details
        """
        base_url = self.base_url.rstrip('/')
        server_url = f"{base_url}/servers/{self.server_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get server details
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                server_url
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
                        "url": server_url,
                        "server_id": self.server_id
                    }
                )
            
            # Try to parse JSON response
            try:
                server_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": server_data,
                        "url": server_url,
                        "server_id": self.server_id,
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
                        "url": server_url,
                        "server_id": self.server_id
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": server_url,
                    "server_id": self.server_id
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": server_url,
                    "server_id": self.server_id
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": server_url,
                    "server_id": self.server_id
                }
            )
