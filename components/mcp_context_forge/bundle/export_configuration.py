"""
MCP Context Forge Export Configuration Component

This component exports configuration from the MCP Context Forge server
by making a curl request to the /export endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ExportConfigurationComponent(Component):
    display_name = "MCP Export Configuration"
    description = "Export configuration from the MCP Context Forge server"
    icon = "download"
    name = "ExportConfigurationComponent"
    
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
            name="types",
            display_name="Entity Types",
            info="Comma-separated entity types to export (e.g., tools,gateways,servers,resources,prompts). Leave empty to export all.",
            value="",
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="export_data", display_name="Export Data", method="export_configuration"),
    ]
    
    def export_configuration(self) -> Data:
        """
        Export configuration from the MCP Context Forge server.
        
        Returns:
            Data: Contains the exported configuration data
        """
        base_url = self.base_url.rstrip('/')
        
        # Build query parameters
        params = []
        if self.types:
            params.append(f"types={self.types}")
        
        query_string = "&".join(params)
        export_url = f"{base_url}/export"
        if query_string:
            export_url += f"?{query_string}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to export configuration
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                export_url
            ]
            
            # Run the curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # Longer timeout for export operations
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "url": export_url
                    }
                )
            
            # Try to parse JSON response
            try:
                export_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": export_data,
                        "url": export_url,
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
                        "url": export_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 30 seconds",
                    "url": export_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": export_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": export_url
                }
            )
