"""
MCP Context Forge Import Configuration Component

This component imports configuration into the MCP Context Forge server
by making a POST request to the /import endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput, BoolInput
from lfx.schema import Data


class ImportConfigurationComponent(Component):
    display_name = "MCP Import Configuration"
    description = "Import configuration into the MCP Context Forge server"
    icon = "upload"
    name = "ImportConfigurationComponent"
    
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
        MultilineInput(
            name="import_data",
            display_name="Import Data",
            info="JSON data to import (exported configuration)",
            required=True,
        ),
        StrInput(
            name="conflict_strategy",
            display_name="Conflict Strategy",
            info="Strategy for handling conflicts: 'skip', 'overwrite', or 'merge'",
            value="skip",
            required=False,
        ),
        BoolInput(
            name="dry_run",
            display_name="Dry Run",
            info="Whether to perform a dry run without actually importing",
            value=False,
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="import_result", display_name="Import Result", method="import_configuration"),
    ]
    
    def import_configuration(self) -> Data:
        """
        Import configuration into the MCP Context Forge server.
        
        Returns:
            Data: Contains the import result
        """
        base_url = self.base_url.rstrip('/')
        import_url = f"{base_url}/import"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Parse import data
        try:
            import_data = json.loads(self.import_data)
        except json.JSONDecodeError as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Invalid JSON in import data: {str(e)}",
                    "url": import_url
                }
            )
        
        # Prepare the JSON payload
        payload = {
            "import_data": import_data,
            "conflict_strategy": self.conflict_strategy,
            "dry_run": self.dry_run
        }
        
        try:
            # Execute curl command to import configuration
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                import_url
            ]
            
            # Run the curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # Longer timeout for import operations
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "url": import_url,
                        "payload": payload
                    }
                )
            
            # Try to parse JSON response
            try:
                import_result = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": import_result,
                        "url": import_url,
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
                        "url": import_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 30 seconds",
                    "url": import_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": import_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": import_url,
                    "payload": payload
                }
            )
