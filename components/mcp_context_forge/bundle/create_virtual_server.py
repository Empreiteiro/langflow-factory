"""
MCP Context Forge Create Virtual Server Component

This component creates a new virtual server in the MCP Context Forge server
by making a POST request to the /servers endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class CreateVirtualServerComponent(Component):
    display_name = "MCP Create Virtual Server"
    description = "Create a new virtual server in the MCP Context Forge server"
    icon = "plus-circle"
    name = "CreateVirtualServerComponent"
    
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
            name="server_name",
            display_name="Server Name",
            info="The name of the virtual server to create",
            value="my-virtual-server",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the virtual server",
            value="Composed server with multiple tools",
            required=False,
        ),
        MultilineInput(
            name="associated_tools",
            display_name="Associated Tools",
            info="JSON array of tool IDs to associate with the server (e.g., [\"tool-id-1\", \"tool-id-2\"])",
            value='["tool-id-1"]',
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="creation_result", display_name="Creation Result", method="create_server"),
    ]
    
    def create_server(self) -> Data:
        """
        Create a new virtual server in the MCP Context Forge server.
        
        Returns:
            Data: Contains the creation result
        """
        base_url = self.base_url.rstrip('/')
        servers_url = f"{base_url}/servers"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Parse associated tools
        try:
            tools = json.loads(self.associated_tools)
            if not isinstance(tools, list):
                tools = [tools]
        except json.JSONDecodeError as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Invalid JSON in associated tools: {str(e)}",
                    "url": servers_url
                }
            )
        
        # Prepare the JSON payload
        payload = {
            "server": {
                "name": self.server_name,
                "associated_tools": tools
            }
        }
        
        # Add description if provided
        if self.description:
            payload["server"]["description"] = self.description
        
        try:
            # Execute curl command to create server
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
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
                        "url": servers_url,
                        "payload": payload
                    }
                )
            
            # Try to parse JSON response
            try:
                creation_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": creation_data,
                        "url": servers_url,
                        "payload": payload,
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
                        "url": servers_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": servers_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": servers_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": servers_url,
                    "payload": payload
                }
            )
