"""
MCP Context Forge Register Gateway Component

This component registers a new MCP server gateway in the MCP Context Forge server
by making a POST request to the /gateways endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class RegisterGatewayComponent(Component):
    display_name = "MCP Register Gateway"
    description = "Register a new MCP server gateway in the MCP Context Forge server"
    icon = "plus"
    name = "RegisterGatewayComponent"
    
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
            name="gateway_name",
            display_name="Gateway Name",
            info="The name of the gateway to register",
            value="my-mcp-server",
            required=True,
        ),
        StrInput(
            name="gateway_url",
            display_name="Gateway URL",
            info="The URL of the MCP server gateway",
            value="http://localhost:9000/mcp",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the gateway",
            value="My custom MCP server",
            required=False,
        ),
        StrInput(
            name="transport",
            display_name="Transport Type",
            info="Transport type for the gateway",
            value="STREAMABLEHTTP",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_gateway"),
    ]
    
    def register_gateway(self) -> Data:
        """
        Register a new MCP server gateway in the MCP Context Forge server.
        
        Returns:
            Data: Contains the registration result
        """
        base_url = self.base_url.rstrip('/')
        gateways_url = f"{base_url}/gateways"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload
        payload = {
            "name": self.gateway_name,
            "url": self.gateway_url,
            "transport": self.transport
        }
        
        # Add description if provided
        if self.description:
            payload["description"] = self.description
        
        try:
            # Execute curl command to register gateway
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
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
                        "url": gateways_url,
                        "payload": payload
                    }
                )
            
            # Try to parse JSON response
            try:
                registration_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": registration_data,
                        "url": gateways_url,
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
                        "url": gateways_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": gateways_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": gateways_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": gateways_url,
                    "payload": payload
                }
            )
