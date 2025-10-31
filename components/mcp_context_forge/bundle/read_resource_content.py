"""
MCP Context Forge Read Resource Content Component

This component reads the content of a specific resource from the MCP Context Forge server
by making a curl request to the /resources/{uri}/read endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional
import urllib.parse

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ReadResourceContentComponent(Component):
    display_name = "MCP Read Resource Content"
    description = "Read the content of a specific resource from the MCP Context Forge server"
    icon = "file-text"
    name = "ReadResourceContentComponent"
    
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
            name="resource_uri",
            display_name="Resource URI",
            info="The URI of the resource to read content from (e.g., file:///etc/config.json)",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="resource_content", display_name="Resource Content", method="read_resource_content"),
    ]
    
    def read_resource_content(self) -> Data:
        """
        Read the content of a specific resource from the MCP Context Forge server.
        
        Returns:
            Data: Contains the resource content
        """
        base_url = self.base_url.rstrip('/')
        
        # URL encode the resource URI for the API call
        encoded_uri = urllib.parse.quote(self.resource_uri, safe='')
        resource_read_url = f"{base_url}/resources/{encoded_uri}/read"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to read resource content
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                resource_read_url
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
                        "url": resource_read_url,
                        "resource_uri": self.resource_uri
                    }
                )
            
            # Try to parse JSON response
            try:
                content_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": content_data,
                        "url": resource_read_url,
                        "resource_uri": self.resource_uri,
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
                        "url": resource_read_url,
                        "resource_uri": self.resource_uri
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": resource_read_url,
                    "resource_uri": self.resource_uri
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": resource_read_url,
                    "resource_uri": self.resource_uri
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": resource_read_url,
                    "resource_uri": self.resource_uri
                }
            )
