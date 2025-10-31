"""
MCP Context Forge List Gateways Component

This component lists all registered gateways in the MCP Context Forge server
by making a curl request to the /gateways endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ListGatewaysComponent(Component):
    display_name = "MCP List Gateways"
    description = "List all registered gateways in the MCP Context Forge server"
    icon = "list"
    name = "ListGatewaysComponent"
    
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
        Output(name="gateways_list", display_name="Gateways List", method="list_gateways"),
    ]
    
    def list_gateways(self) -> Data:
        """
        List all registered gateways in the MCP Context Forge server.
        
        Returns:
            Data: Contains the list of registered gateways
        """
        base_url = self.base_url.rstrip('/')
        gateways_url = f"{base_url}/gateways"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to list gateways
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                gateways_url
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
                        "url": gateways_url
                    }
                )
            
            # Try to parse JSON response
            try:
                gateways_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": gateways_data,
                        "url": gateways_url,
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
                        "url": gateways_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": gateways_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": gateways_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": gateways_url
                }
            )
