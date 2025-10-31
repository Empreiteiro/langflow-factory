"""
MCP Context Forge Register Custom Tool Component

This component registers a custom tool in the MCP Context Forge server
by making a POST request to the /tools endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class RegisterCustomToolComponent(Component):
    display_name = "MCP Register Custom Tool"
    description = "Register a custom tool in the MCP Context Forge server"
    icon = "plus-circle"
    name = "RegisterCustomToolComponent"
    
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
            name="tool_name",
            display_name="Tool Name",
            info="The name of the tool to register",
            value="weather-api",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the tool",
            value="Get weather information for a city",
            required=True,
        ),
        StrInput(
            name="url",
            display_name="Tool URL",
            info="The URL endpoint for the tool",
            value="https://api.weather.com/v1/current",
            required=True,
        ),
        StrInput(
            name="integration_type",
            display_name="Integration Type",
            info="Type of integration (e.g., REST)",
            value="REST",
            required=True,
        ),
        StrInput(
            name="request_type",
            display_name="Request Type",
            info="HTTP request type (GET, POST, PUT, DELETE)",
            value="POST",
            required=True,
        ),
        MultilineInput(
            name="input_schema",
            display_name="Input Schema",
            info="JSON schema for tool input parameters",
            value='{\n  "type": "object",\n  "properties": {\n    "city": {\n      "type": "string",\n      "description": "City name"\n    }\n  },\n  "required": ["city"]\n}',
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_tool"),
    ]
    
    def register_tool(self) -> Data:
        """
        Register a custom tool in the MCP Context Forge server.
        
        Returns:
            Data: Contains the registration result
        """
        base_url = self.base_url.rstrip('/')
        tools_url = f"{base_url}/tools"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Parse input schema
        try:
            input_schema = json.loads(self.input_schema)
        except json.JSONDecodeError as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Invalid JSON in input schema: {str(e)}",
                    "url": tools_url
                }
            )
        
        # Prepare the JSON payload
        payload = {
            "tool": {
                "name": self.tool_name,
                "description": self.description,
                "url": self.url,
                "integration_type": self.integration_type,
                "request_type": self.request_type,
                "input_schema": input_schema
            }
        }
        
        try:
            # Execute curl command to register tool
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                tools_url
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
                        "url": tools_url,
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
                        "url": tools_url,
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
                        "url": tools_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": tools_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": tools_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": tools_url,
                    "payload": payload
                }
            )
