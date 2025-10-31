"""
MCP Context Forge Update Prompt Component

This component updates a prompt template in the MCP Context Forge server
by making a PUT request to the /prompts/{prompt_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class UpdatePromptComponent(Component):
    display_name = "MCP Update Prompt"
    description = "Update a prompt template in the MCP Context Forge server"
    icon = "edit"
    name = "UpdatePromptComponent"
    
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
            name="prompt_id",
            display_name="Prompt ID",
            info="The ID of the prompt to update",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="The new description for the prompt",
            required=False,
        ),
        MultilineInput(
            name="template",
            display_name="Template",
            info="The new template content (optional)",
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="update_result", display_name="Update Result", method="update_prompt"),
    ]
    
    def update_prompt(self) -> Data:
        """
        Update a prompt template in the MCP Context Forge server.
        
        Returns:
            Data: Contains the update result
        """
        base_url = self.base_url.rstrip('/')
        prompt_url = f"{base_url}/prompts/{self.prompt_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Prepare the JSON payload with only provided fields
        payload = {}
        
        if self.description:
            payload["description"] = self.description
        
        if self.template:
            payload["content"] = self.template
        
        try:
            # Execute curl command to update prompt
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "PUT",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                prompt_url
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
                        "url": prompt_url,
                        "prompt_id": self.prompt_id,
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
                        "url": prompt_url,
                        "prompt_id": self.prompt_id,
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
                        "url": prompt_url,
                        "prompt_id": self.prompt_id,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "payload": payload
                }
            )
