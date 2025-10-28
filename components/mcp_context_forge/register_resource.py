"""
MCP Context Forge Register Resource Component

This component registers a new resource in the MCP Context Forge server
by making a POST request to the /resources endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class RegisterResourceComponent(Component):
    display_name = "MCP Register Resource"
    description = "Register a new resource in the MCP Context Forge server"
    icon = "plus-circle"
    name = "RegisterResourceComponent"
    
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
            name="resource_name",
            display_name="Resource Name",
            info="The name of the resource to register",
            value="config-file",
            required=True,
        ),
        StrInput(
            name="uri",
            display_name="URI",
            info="The URI of the resource (e.g., file:///etc/config.json)",
            value="file:///etc/config.json",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the resource",
            value="Application configuration file",
            required=False,
        ),
        StrInput(
            name="mime_type",
            display_name="MIME Type",
            info="The MIME type of the resource",
            value="application/json",
            required=False,
        ),
        MultilineInput(
            name="content",
            display_name="Content",
            info="The content of the resource (optional)",
            value='{"key": "value"}',
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_resource"),
    ]
    
    def register_resource(self) -> Data:
        """
        Register a new resource in the MCP Context Forge server.
        
        Returns:
            Data: Contains the registration result
        """
        base_url = self.base_url.rstrip('/')
        resources_url = f"{base_url}/resources"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload
        resource_data = {
            "name": self.resource_name,
            "uri": self.uri
        }
        
        # Add optional fields if provided
        if self.description:
            resource_data["description"] = self.description
        
        if self.mime_type:
            resource_data["mime_type"] = self.mime_type
        
        if self.content:
            resource_data["content"] = self.content
        
        payload = {
            "resource": resource_data
        }
        
        try:
            # Execute curl command to register resource
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                resources_url
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
                        "url": resources_url,
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
                        "url": resources_url,
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
                        "url": resources_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": resources_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": resources_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": resources_url,
                    "payload": payload
                }
            )
