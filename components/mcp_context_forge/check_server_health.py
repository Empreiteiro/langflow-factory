"""
MCP Context Forge Server Health Check Component

This component checks the health status of an MCP Context Forge server
by making a curl request to the /health endpoint and parsing the JSON response.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, Output
from lfx.schema import Data


class CheckServerHealthComponent(Component):
    display_name = "MCP Server Health Check"
    description = "Check the health status of an MCP Context Forge server"
    icon = "heart"
    name = "CheckServerHealthComponent"
    
    inputs = [
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="The base URL of the MCP Context Forge server (e.g., http://localhost:4444)",
            value="http://localhost:4444",
        ),
    ]
    
    outputs = [
        Output(name="health_status", display_name="Health Status", method="check_health"),
    ]
    
    def check_health(self) -> Data:
        """
        Check the health status of the MCP Context Forge server.
        
        Returns:
            Data: Contains the health status information from the server
        """
        base_url = self.base_url.rstrip('/')
        health_url = f"{base_url}/health"
        
        try:
            # Execute curl command to check server health
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                health_url
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
                        "url": health_url
                    }
                )
            
            # Try to parse JSON response
            try:
                health_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": health_data,
                        "url": health_url,
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
                        "url": health_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                        "url": health_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                        "url": health_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                        "url": health_url
                }
            )