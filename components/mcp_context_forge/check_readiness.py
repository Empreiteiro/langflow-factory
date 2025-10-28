"""
MCP Context Forge Server Readiness Check Component

This component checks the readiness status of an MCP Context Forge server
by making a curl request to the /ready endpoint and parsing the JSON response.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, Output
from lfx.schema import Data


class CheckServerReadinessComponent(Component):
    display_name = "MCP Server Readiness Check"
    description = "Check the readiness status of an MCP Context Forge server"
    icon = "check-circle"
    name = "CheckServerReadinessComponent"
    
    inputs = [
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="The base URL of the MCP Context Forge server (e.g., http://localhost:4444)",
            value="http://localhost:4444",
        ),
    ]
    
    outputs = [
        Output(name="readiness_status", display_name="Readiness Status", method="check_readiness"),
    ]
    
    def check_readiness(self) -> Data:
        """
        Check the readiness status of the MCP Context Forge server.
        
        Returns:
            Data: Contains the readiness status information from the server
        """
        base_url = self.base_url.rstrip('/')
        readiness_url = f"{base_url}/ready"
        
        try:
            # Execute curl command to check server readiness
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                readiness_url
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
                        "url": readiness_url
                    }
                )
            
            # Try to parse JSON response
            try:
                readiness_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": readiness_data,
                        "url": readiness_url,
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
                        "url": readiness_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": readiness_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": readiness_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": readiness_url
                }
            )
