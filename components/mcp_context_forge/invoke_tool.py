"""
MCP Context Forge Invoke Tool Component

This component invokes a tool with arguments in the MCP Context Forge server
by making a POST request to the /rpc endpoint with JSON-RPC format.
"""

import subprocess
import json
from typing import Optional

from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, MultilineInput
from lfx.schema import Data


class InvokeToolComponent(Component):
    display_name = "MCP Invoke Tool"
    description = "Invoke a tool with arguments in the MCP Context Forge server"
    icon = "play"
    name = "InvokeToolComponent"
    
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
            name="tool_name",
            display_name="Tool Name",
            info="The name of the tool to invoke",
            required=True,
        ),
        MultilineInput(
            name="arguments",
            display_name="Arguments",
            info="JSON object with tool arguments (e.g., {\"param1\":\"value1\",\"param2\":\"value2\"})",
            value='{"param1":"value1","param2":"value2"}',
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="invoke_result", display_name="Invoke Result", method="invoke_tool"),
    ]
    
    def invoke_tool(self) -> Data:
        """
        Invoke a tool with arguments in the MCP Context Forge server.
        
        Returns:
            Data: Contains the tool execution result
        """
        base_url = self.base_url.rstrip('/')
        rpc_url = f"{base_url}/rpc"
        
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
                    "url": rpc_url
                }
            )
        
        # Prepare JSON-RPC payload
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": self.tool_name,
                "arguments": args
            }
        }
        
        try:
            # Execute curl command to invoke tool
            curl_command = [
                "curl", 
                "-s",  # Silent mode
                "-X", "POST",
                "-H", f"Authorization: Bearer {token_value}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                rpc_url
            ]
            
            # Run the curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # Longer timeout for tool execution
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "url": rpc_url,
                        "tool_name": self.tool_name,
                        "arguments": args
                    }
                )
            
            # Try to parse JSON response
            try:
                invoke_data = json.loads(result.stdout)
                
                # Extract result content if available
                if "result" in invoke_data and "content" in invoke_data["result"]:
                    content = invoke_data["result"]["content"]
                    if content and len(content) > 0 and "text" in content[0]:
                        invoke_data["extracted_text"] = content[0]["text"]
                
                return Data(
                    value={
                        "status": "success",
                        "data": invoke_data,
                        "url": rpc_url,
                        "tool_name": self.tool_name,
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
                        "url": rpc_url,
                        "tool_name": self.tool_name,
                        "arguments": args
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 30 seconds",
                    "url": rpc_url,
                    "tool_name": self.tool_name,
                    "arguments": args
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH",
                    "url": rpc_url,
                    "tool_name": self.tool_name,
                    "arguments": args
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": rpc_url,
                    "tool_name": self.tool_name,
                    "arguments": args
                }
            )
