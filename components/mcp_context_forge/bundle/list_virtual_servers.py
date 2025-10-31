"""
MCP Context Forge List Virtual Servers Component

This component lists all virtual servers in the MCP Context Forge server
by making a curl request to the /servers endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ListVirtualServersComponent(Component):
    display_name = "MCP List Virtual Servers"
    description = "List all virtual servers in the MCP Context Forge server"
    icon = "server"
    name = "ListVirtualServersComponent"
    
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
        Output(name="servers_list", display_name="Servers List", method="list_servers"),
    ]
    
    def list_servers(self) -> Data:
        """
        List all virtual servers in the MCP Context Forge server.
        
        Returns:
            Data: Contains the list of virtual servers
        """
        base_url = self.base_url.rstrip('/')
        servers_url = f"{base_url}/servers"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to list servers
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                servers_url
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
                        "url": servers_url
                    }
                )
            
            # Try to parse JSON response
            try:
                servers_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": servers_data,
                        "url": servers_url,
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
                        "url": servers_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": servers_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": servers_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": servers_url
                }
            )
