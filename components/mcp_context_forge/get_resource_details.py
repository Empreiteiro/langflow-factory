"""
MCP Context Forge Get Resource Details Component

This component retrieves details of a specific resource by URI from the MCP Context Forge server
by making a curl request to the /resources/{uri} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional
import urllib.parse

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetResourceDetailsComponent(Component):
    display_name = "MCP Get Resource Details"
    description = "Get details of a specific resource by URI from the MCP Context Forge server"
    icon = "info"
    name = "GetResourceDetailsComponent"
    
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
            info="The URI of the resource to retrieve details for (e.g., file:///etc/config.json)",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="resource_details", display_name="Resource Details", method="get_resource_details"),
    ]
    
    def get_resource_details(self) -> Data:
        """
        Get details of a specific resource by URI from the MCP Context Forge server.
        
        Returns:
            Data: Contains the resource details including content
        """
        base_url = self.base_url.rstrip('/')
        
        # URL encode the resource URI for the API call
        encoded_uri = urllib.parse.quote(self.resource_uri, safe='')
        resource_url = f"{base_url}/resources/{encoded_uri}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get resource details
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                resource_url
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
                        "url": resource_url,
                        "resource_uri": self.resource_uri
                    }
                )
            
            # Try to parse JSON response
            try:
                resource_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": resource_data,
                        "url": resource_url,
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
                        "url": resource_url,
                        "resource_uri": self.resource_uri
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": resource_url,
                    "resource_uri": self.resource_uri
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": resource_url,
                    "resource_uri": self.resource_uri
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": resource_url,
                    "resource_uri": self.resource_uri
                }
            )
