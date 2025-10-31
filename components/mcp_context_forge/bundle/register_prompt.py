"""
MCP Context Forge Register Prompt Component

This component registers a new prompt template in the MCP Context Forge server
by making a POST request to the /prompts endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class RegisterPromptComponent(Component):
    display_name = "MCP Register Prompt"
    description = "Register a new prompt template in the MCP Context Forge server"
    icon = "plus-circle"
    name = "RegisterPromptComponent"
    
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
            name="prompt_name",
            display_name="Prompt Name",
            info="The name of the prompt template to register",
            value="code-review",
            required=True,
        ),
        StrInput(
            name="description",
            display_name="Description",
            info="Description of the prompt template",
            value="Review code for best practices",
            required=False,
        ),
        MultilineInput(
            name="template",
            display_name="Template",
            info="The prompt template with placeholders (e.g., Review the following code: {{code}})",
            value="Review the following code and suggest improvements:\n\n{{code}}",
            required=True,
        ),
        MultilineInput(
            name="arguments",
            display_name="Arguments",
            info="JSON array of template arguments (e.g., [{\"name\": \"code\", \"description\": \"Code to review\", \"required\": true}])",
            value='[{"name": "code", "description": "Code to review", "required": true}]',
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="registration_result", display_name="Registration Result", method="register_prompt"),
    ]
    
    def register_prompt(self) -> Data:
        """
        Register a new prompt template in the MCP Context Forge server.
        
        Returns:
            Data: Contains the registration result
        """
        base_url = self.base_url.rstrip('/')
        prompts_url = f"{base_url}/prompts"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Parse arguments
        try:
            args = json.loads(self.arguments)
            if not isinstance(args, list):
                args = [args]
        except json.JSONDecodeError as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Invalid JSON in arguments: {str(e)}",
                    "url": prompts_url
                }
            )
        
        # Prepare the JSON payload
        prompt_data = {
            "name": self.prompt_name,
            "template": self.template,
            "arguments": args
        }
        
        # Add description if provided
        if self.description:
            prompt_data["description"] = self.description
        
        payload = {
            "prompt": prompt_data
        }
        
        try:
            # Execute curl command to register prompt
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                prompts_url
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
                        "url": prompts_url,
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
                        "url": prompts_url,
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
                        "url": prompts_url,
                        "payload": payload
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": prompts_url,
                    "payload": payload
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": prompts_url,
                    "payload": payload
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": prompts_url,
                    "payload": payload
                }
            )
