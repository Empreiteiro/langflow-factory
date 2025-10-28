"""
MCP Context Forge Server Version Check Component

This component checks the version information of an MCP Context Forge server
by making a curl request to the /version endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class CheckServerVersionComponent(Component):
    display_name = "MCP Server Version Check"
    description = "Check the version information of an MCP Context Forge server"
    icon = "info"
    name = "CheckServerVersionComponent"
    
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
        Output(name="version_info", display_name="Version Information", method="check_version"),
    ]
    
    def check_version(self) -> Data:
        """
        Check the version information of the MCP Context Forge server.
        
        Returns:
            Data: Contains the version information from the server
        """
        base_url = self.base_url.rstrip('/')
        version_url = f"{base_url}/version"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to check server version
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                version_url
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
                        "url": version_url
                    }
                )
            
            # Try to parse JSON response
            try:
                version_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": version_data,
                        "url": version_url,
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
                        "url": version_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": version_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": version_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": version_url
                }
            )
