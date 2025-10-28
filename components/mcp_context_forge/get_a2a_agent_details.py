"""
MCP Context Forge Get A2A Agent Details Component

This component retrieves details of a specific A2A agent by ID from the MCP Context Forge server
by making a curl request to the /a2a/{agent_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class GetA2AAgentDetailsComponent(Component):
    display_name = "MCP Get A2A Agent Details"
    description = "Get details of a specific A2A agent by ID from the MCP Context Forge server"
    icon = "info"
    name = "GetA2AAgentDetailsComponent"
    
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
            name="agent_id",
            display_name="Agent ID",
            info="The ID of the A2A agent to retrieve details for",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="agent_details", display_name="Agent Details", method="get_agent_details"),
    ]
    
    def get_agent_details(self) -> Data:
        """
        Get details of a specific A2A agent by ID from the MCP Context Forge server.
        
        Returns:
            Data: Contains the A2A agent details
        """
        base_url = self.base_url.rstrip('/')
        agent_url = f"{base_url}/a2a/{self.agent_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to get A2A agent details
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-H", f"Authorization: Bearer {token_value}",
                agent_url
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
                        "url": agent_url,
                        "agent_id": self.agent_id
                    }
                )
            
            # Try to parse JSON response
            try:
                agent_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": agent_data,
                        "url": agent_url,
                        "agent_id": self.agent_id,
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
                        "url": agent_url,
                        "agent_id": self.agent_id
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": agent_url,
                    "agent_id": self.agent_id
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": agent_url,
                    "agent_id": self.agent_id
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": agent_url,
                    "agent_id": self.agent_id
                }
            )
