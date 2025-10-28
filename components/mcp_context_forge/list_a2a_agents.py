"""
MCP Context Forge List A2A Agents Component

This component lists all registered A2A (Agent-to-Agent) agents in the MCP Context Forge server
by making a curl request to the /a2a endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class ListA2AAgentsComponent(Component):
    display_name = "MCP List A2A Agents"
    description = "List all registered A2A (Agent-to-Agent) agents in the MCP Context Forge server"
    icon = "users"
    name = "ListA2AAgentsComponent"
    
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
        Output(name="agents_list", display_name="Agents List", method="list_agents"),
    ]
    
    def list_agents(self) -> Data:
        """
        List all registered A2A agents in the MCP Context Forge server.
        
        Returns:
            Data: Contains the list of registered A2A agents
        """
        base_url = self.base_url.rstrip('/')
        agents_url = f"{base_url}/a2a"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to list A2A agents
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                agents_url
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
                        "url": agents_url
                    }
                )
            
            # Try to parse JSON response
            try:
                agents_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": agents_data,
                        "url": agents_url,
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
                        "url": agents_url
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": agents_url
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": agents_url
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": agents_url
                }
            )
