"""
MCP Context Forge Invoke A2A Agent Component

This component invokes an A2A agent with a message in the MCP Context Forge server
by making a POST request to the /a2a/{agent_name}/invoke endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class InvokeA2AAgentComponent(Component):
    display_name = "MCP Invoke A2A Agent"
    description = "Invoke an A2A agent with a message in the MCP Context Forge server"
    icon = "play"
    name = "InvokeA2AAgentComponent"
    
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
            info="The name of the A2A agent to invoke",
            required=True,
        ),
        MultilineInput(
            name="message",
            display_name="Message",
            info="The message to send to the A2A agent",
            value="Explain quantum computing in simple terms",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="invoke_result", display_name="Invoke Result", method="invoke_agent"),
    ]
    
    def invoke_agent(self) -> Data:
        """
        Invoke an A2A agent with a message in the MCP Context Forge server.
        
        Returns:
            Data: Contains the agent response
        """
        base_url = self.base_url.rstrip('/')
        invoke_url = f"{base_url}/a2a/{self.agent_name}/invoke"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload
        payload = {
            "message": self.message
        }
        
        try:
            # Execute curl command to invoke A2A agent
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                invoke_url
            ]
            
            # Run the curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # Longer timeout for agent execution
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "url": invoke_url,
                        "agent_name": self.agent_name,
                        "message": self.message
                    }
                )
            
            # Try to parse JSON response
            try:
                invoke_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": invoke_data,
                        "url": invoke_url,
                        "agent_name": self.agent_name,
                        "message": self.message,
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
                        "url": invoke_url,
                        "agent_name": self.agent_name,
                        "message": self.message
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 30 seconds",
                    "url": invoke_url,
                    "agent_name": self.agent_name,
                    "message": self.message
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": invoke_url,
                    "agent_name": self.agent_name,
                    "message": self.message
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": invoke_url,
                    "agent_name": self.agent_name,
                    "message": self.message
                }
            )
