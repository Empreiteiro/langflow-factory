"""
MCP Context Forge Update A2A Agent Component

This component updates an A2A agent configuration in the MCP Context Forge server
by making a PUT request to the /a2a/{agent_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class UpdateA2AAgentComponent(Component):
    display_name = "MCP Update A2A Agent"
    description = "Update an A2A agent configuration in the MCP Context Forge server"
    icon = "edit"
    name = "UpdateA2AAgentComponent"
    
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
            info="The ID of the A2A agent to update",
            required=True,
        ),
        StrInput(
            name="model",
            display_name="Model",
            info="The model to use (e.g., gpt-4-turbo)",
            required=False,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Updated description for the agent",
            required=False,
        ),
        MultilineInput(
            name="additional_config",
            display_name="Additional Config",
            info="Additional configuration as JSON (optional)",
            value='{}',
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="update_result", display_name="Update Result", method="update_agent"),
    ]
    
    def update_agent(self) -> Data:
        """
        Update an A2A agent configuration in the MCP Context Forge server.
        
        Returns:
            Data: Contains the update result
        """
        base_url = self.base_url.rstrip('/')
        agent_url = f"{base_url}/a2a/{self.agent_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload with only provided fields
        payload = {}
        
        if self.model:
            payload["model"] = self.model
        
        if self.description:
            payload["description"] = self.description
        
        # Parse additional config if provided
        if self.additional_config and self.additional_config.strip():
            try:
                additional_config = json.loads(self.additional_config)
                payload.update(additional_config)
            except json.JSONDecodeError as e:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Invalid JSON in additional config: {str(e)}",
                        "url": agent_url
                    }
                )
        
        try:
            # Execute curl command to update A2A agent
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "PUT",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
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
                        "agent_id": self.agent_id,
                        "payload": payload
                    }
                )
            
            # Try to parse JSON response
            try:
                update_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": update_data,
                        "url": agent_url,
                        "agent_id": self.agent_id,
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
                        "url": agent_url,
                        "agent_id": self.agent_id,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": agent_url,
                    "agent_id": self.agent_id,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": agent_url,
                    "agent_id": self.agent_id,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": agent_url,
                    "agent_id": self.agent_id,
                    "payload": payload
                }
            )
