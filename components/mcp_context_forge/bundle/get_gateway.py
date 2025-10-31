"""
MCP Context Forge Get Gateway Component

This component retrieves a specific gateway by ID from the MCP Context Forge server
by making a curl request to the /gateways/{gateway_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetGatewayComponent(Component):
    display_name = "MCP Get Gateway"
    description = "Get a specific gateway by ID from the MCP Context Forge server"
    icon = "search"
    name = "GetGatewayComponent"
    
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
            name="gateway_id",
            display_name="Gateway ID",
            info="The ID of the gateway to retrieve",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="gateway_info", display_name="Gateway Information", method="get_gateway"),
    ]
    
    def get_gateway(self) -> Data:
        """
        Get a specific gateway by ID from the MCP Context Forge server.
        
        Returns:
            Data: Contains the gateway information
        """
        base_url = self.base_url.rstrip('/')
        gateway_url = f"{base_url}/gateways/{self.gateway_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get gateway
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                gateway_url
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
                        "url": gateway_url,
                        "gateway_id": self.gateway_id
                    }
                )
            
            # Try to parse JSON response
            try:
                gateway_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": gateway_data,
                        "url": gateway_url,
                        "gateway_id": self.gateway_id,
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
                        "url": gateway_url,
                        "gateway_id": self.gateway_id
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": gateway_url,
                    "gateway_id": self.gateway_id
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": gateway_url,
                    "gateway_id": self.gateway_id
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": gateway_url,
                    "gateway_id": self.gateway_id
                }
            )
