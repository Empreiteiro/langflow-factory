"""
MCP Context Forge Register A2A Agent Component

This component registers a new A2A (Agent-to-Agent) agent in the MCP Context Forge server
by making a POST request to the /a2a endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class RegisterA2AAgentComponent(Component):
    display_name = "MCP Register A2A Agent"
    description = "Register a new A2A (Agent-to-Agent) agent in the MCP Context Forge server"
    icon = "plus-circle"
    name = "RegisterA2AAgentComponent"
    
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
            name="agent_name",
            display_name="Agent Name",
            info="The name of the A2A agent to register",
            value="openai-assistant",
            required=True,
        ),
        StrInput(
            name="agent_type",
            display_name="Agent Type",
            info="The type of agent (e.g., openai, claude, custom)",
            value="openai",
            required=True,
        ),
        StrInput(
            name="endpoint_url",
            display_name="Endpoint URL",
            info="The endpoint URL for the agent",
            value="https://api.openai.com/v1/chat/completions",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the A2A agent",
            value="OpenAI GPT-4 assistant",
            required=False,
        ),
        StrInput(
            name="auth_type",
            display_name="Auth Type",
            info="Authentication type (e.g., bearer, api_key)",
            value="bearer",
            required=False,
        ),
        StrInput(
            name="auth_value",
            display_name="Auth Value",
            info="Authentication value or environment variable name",
            value="OPENAI_API_KEY",
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_agent"),
    ]
    
    def register_agent(self) -> Data:
        """
        Register a new A2A agent in the MCP Context Forge server.
        
        Returns:
            Data: Contains the registration result
        """
        base_url = self.base_url.rstrip('/')
        agents_url = f"{base_url}/a2a"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload
        agent_data = {
            "name": self.agent_name,
            "agent_type": self.agent_type,
            "endpoint_url": self.endpoint_url
        }
        
        # Add optional fields if provided
        if self.description:
            agent_data["description"] = self.description
        
        if self.auth_type:
            agent_data["auth_type"] = self.auth_type
        
        if self.auth_value:
            agent_data["auth_value"] = self.auth_value
        
        payload = {
            "agent": agent_data
        }
        
        try:
            # Execute curl command to register A2A agent
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
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
                        "url": agents_url,
                        "payload": payload
                    }
                )
            
            # Try to parse JSON response
            try:
                registration_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": registration_data,
                        "url": agents_url,
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
                        "url": agents_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": agents_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": agents_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": agents_url,
                    "payload": payload
                }
            )
