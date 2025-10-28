"""
MCP Context Forge Delete Prompt Component

This component deletes a prompt from the MCP Context Forge server
by making a DELETE request to the /prompts/{prompt_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data


class DeletePromptComponent(Component):
    display_name = "MCP Delete Prompt"
    description = "Delete a prompt from the MCP Context Forge server"
    icon = "trash"
    name = "DeletePromptComponent"
    
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
            info="The ID of the prompt to delete",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="delete_result", display_name="Delete Result", method="delete_prompt"),
    ]
    
    def delete_prompt(self) -> Data:
        """
        Delete a prompt from the MCP Context Forge server.
        
        Returns:
            Data: Contains the delete result
        """
        base_url = self.base_url.rstrip('/')
        prompt_url = f"{base_url}/prompts/{self.prompt_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        try:
            # Execute curl command to delete prompt
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "DELETE",
                "-H", f"Authorization: Bearer {token_value}",
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
                        "prompt_id": self.prompt_id
                    }
                )
            
            # Try to parse JSON response
            try:
                delete_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": delete_data,
                        "url": prompt_url,
                        "prompt_id": self.prompt_id,
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
                        "prompt_id": self.prompt_id
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id
                }
            )
