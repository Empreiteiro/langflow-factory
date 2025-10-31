"""
MCP Context Forge Register Tool Component

This component registers a new tool in the MCP Context Forge server
by making a POST request to the /tools endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class RegisterToolComponent(Component):
    display_name = "MCP Register Tool"
    description = "Register a new tool in the MCP Context Forge server"
    icon = "plus-circle"
    name = "RegisterToolComponent"
    
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
            value="clock_tool",
            required=True,
        ),
        StrInput(
            name="url",
            display_name="URL",
            info="The URL endpoint for the tool (e.g., http://localhost:9000/rpc)",
            value="http://localhost:9000/rpc",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the tool",
            value="Returns current time",
            required=False,
        ),
        MultilineInput(
            name="input_schema",
            display_name="Input Schema",
            info="JSON schema for tool input parameters (e.g., {\"type\":\"object\",\"properties\":{\"timezone\":{\"type\":\"string\"}},\"required\":[]})",
            value='{"type":"object","properties":{"timezone":{"type":"string"}},"required":[]}',
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_tool"),
    ]
    
    def register_tool(self) -> Data:
        """
        Register a new tool in the MCP Context Forge server.
        
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
        
        # Prepare the JSON payload
        tool_data = {
            "name": self.tool_name,
            "url": self.url
        }
        
        # Add optional fields if provided
        if self.description:
            tool_data["description"] = self.description
        
        if self.input_schema:
            try:
                # Parse the input_schema JSON string if it's a string
                if isinstance(self.input_schema, str):
                    tool_data["input_schema"] = json.loads(self.input_schema)
                elif isinstance(self.input_schema, dict):
                    tool_data["input_schema"] = self.input_schema
                else:
                    tool_data["input_schema"] = self.input_schema
            except json.JSONDecodeError as e:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Invalid JSON in input_schema: {str(e)}",
                        "url": tools_url
                    }
                )
        
        payload = tool_data
        
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

