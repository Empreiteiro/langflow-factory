"""
MCP Context Forge Execute Prompt Component

This component executes a prompt template with arguments in the MCP Context Forge server
by making a POST request to the /prompts/{prompt_id} endpoint with Bearer token authentication.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class ExecutePromptComponent(Component):
    display_name = "MCP Execute Prompt"
    description = "Execute a prompt template with arguments in the MCP Context Forge server"
    icon = "play"
    name = "ExecutePromptComponent"
    
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
            info="The ID of the prompt to execute",
            required=True,
        ),
        MultilineInput(
            name="arguments",
            display_name="Arguments",
            info="JSON object with prompt arguments (e.g., {\"code\": \"function test() { return 1; }\"})",
            value='{"code": "def hello():\n    print(\"Hello\")"}',
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="execution_result", display_name="Execution Result", method="execute_prompt"),
    ]
    
    def execute_prompt(self) -> Data:
        """
        Execute a prompt template with arguments in the MCP Context Forge server.
        
        Returns:
            Data: Contains the rendered prompt content
        """
        base_url = self.base_url.rstrip('/')
        prompt_url = f"{base_url}/prompts/{self.prompt_id}"
        
        # Get token value
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        
        # Parse arguments
        try:
            args = json.loads(self.arguments)
        except json.JSONDecodeError as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Invalid JSON in arguments: {str(e)}",
                    "url": prompt_url
                }
            )
        
        try:
            # Execute curl command to execute prompt
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(args),
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
                        "arguments": args
                    }
                )
            
            # Try to parse JSON response
            try:
                execution_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": execution_data,
                        "url": prompt_url,
                        "prompt_id": self.prompt_id,
                        "arguments": args,
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
                        "arguments": args
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 10 seconds",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "arguments": args
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "arguments": args
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": prompt_url,
                    "prompt_id": self.prompt_id,
                    "arguments": args
                }
            )
