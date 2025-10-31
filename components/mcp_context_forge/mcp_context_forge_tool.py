"""
MCP Context Forge All-in-One Component

This component consolidates all MCP Context Forge actions into a single unified interface.
Each action appears as a separate output/tool. Connect to the desired output to execute that specific action.
"""

import subprocess
import json
from typing import Optional
from urllib.parse import quote

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, MultilineInput, BoolInput, IntInput, DataInput
from langflow.schema import Data

class MCPContextForgeAllComponent(Component):
    display_name = "MCP Context Forge"
    description = "Unified component for all MCP Context Forge operations. Each action appears as a separate output. Connect to the desired output to execute that specific action."
    icon = "server"
    name = "MCPContextForgeAllComponent"
    
    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the MCP action. Connect any component output here to trigger the action.",
            required=False,
        ),
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="The base URL of the MCP Context Forge server (e.g., http://localhost:4444)",
            value="http://localhost:4444",
        ),
        SecretStrInput(
            name="token",
            display_name="Bearer Token",
            info="The Bearer token for authentication (required for most actions)",
            required=False,

        ),
        # Common inputs (initially hidden)
        StrInput(name="gateway_id", display_name="Gateway ID", show=False, info="The ID of the gateway",tool_mode=True),
        StrInput(name="gateway_name", display_name="Gateway Name", show=False, info="The name of the gateway",tool_mode=True),
        StrInput(name="gateway_url", display_name="Gateway URL", show=False, info="The URL of the gateway",tool_mode=True),
        StrInput(name="gateway_description", display_name="Gateway Description", show=False, info="Description of the gateway",tool_mode=True),
        StrInput(name="transport", display_name="Transport Type", show=False, info="Transport type for the gateway",tool_mode=True),
        BoolInput(name="gateway_enabled", display_name="Gateway Enabled", show=False, info="Whether the gateway is enabled",tool_mode=True),
        BoolInput(name="activate", display_name="Activate", show=False, info="Set to true to activate, false to deactivate",tool_mode=True),
        StrInput(name="tool_id", display_name="Tool ID", show=False, info="The ID of the tool",tool_mode=True),
        StrInput(name="tool_name", display_name="Tool Name", show=False, info="The name of the tool",tool_mode=True),
        StrInput(name="tool_description", display_name="Tool Description", show=False, info="Description of the tool",tool_mode=True),
        StrInput(name="tool_url", display_name="Tool URL", show=False, info="The URL endpoint for the tool",tool_mode=True),
        StrInput(name="integration_type", display_name="Integration Type", show=False, info="Type of integration (e.g., REST)）。",tool_mode=True),
        StrInput(name="request_type", display_name="Request Type", show=False, info="HTTP request type (GET, POST, PUT, DELETE)",tool_mode=True),
        MultilineInput(name="input_schema", display_name="Input Schema", show=False, info="JSON schema for tool input parameters",tool_mode=True),
        MultilineInput(name="tool_arguments", display_name="Tool Arguments", show=False, info="JSON object with tool arguments",tool_mode=True),
        BoolInput(name="tool_enabled", display_name="Tool Enabled", show=False, info="Whether the tool is enabled",tool_mode=True),
        StrInput(name="server_id", display_name="Server ID", show=False, info="The ID of the virtual server",tool_mode=True),
        StrInput(name="server_name", display_name="Server Name", show=False, info="The name of the virtual server",tool_mode=True),
        StrInput(name="server_description", display_name="Server Description", show=False, info="Description of the virtual server",tool_mode=True),
        MultilineInput(name="associated_tools", display_name="Associated Tools", show=False, info="JSON array of tool IDs to associate with the server",tool_mode=True),
        StrInput(name="resource_uri", display_name="Resource URI", show=False, info="The URI of the resource",tool_mode=True),
        StrInput(name="resource_name", display_name="Resource Name", show=False, info="The name of the resource",tool_mode=True),
        StrInput(name="resource_description", display_name="Resource Description", show=False, info="Description of the resource",tool_mode=True),
        StrInput(name="mime_type", display_name="MIME Type", show=False, info="MIME type of the resource",tool_mode=True),
        MultilineInput(name="resource_content", display_name="Resource Content", show=False, info="Content of the resource",tool_mode=True),
        StrInput(name="prompt_id", display_name="Prompt ID", show=False, info="The ID of the prompt",tool_mode=True),
        StrInput(name="prompt_name", display_name="Prompt Name", show=False, info="The name of the prompt",tool_mode=True),
        StrInput(name="prompt_description", display_name="Prompt Description", show=False, info="Description of the prompt",tool_mode=True),
        MultilineInput(name="template", display_name="Template", show=False, info="Prompt template with placeholders",tool_mode=True),
        MultilineInput(name="prompt_arguments", display_name="Prompt Arguments", show=False, info="JSON object with prompt arguments",tool_mode=True),
        BoolInput(name="prompt_enabled", display_name="Prompt Enabled", show=False, info="Whether the prompt is enabled",tool_mode=True),
        StrInput(name="tag_name", display_name="Tag Name", show=False, info="The name of the tag",tool_mode=True),
        StrInput(name="entity_types", display_name="Entity Types", show=False, info="Comma-separated entity types (gateways,servers,tools,resources,prompts)",tool_mode=True),
        BoolInput(name="include_entities", display_name="Include Entities", show=False, info="Whether to include entities in the response",tool_mode=True),
        StrInput(name="export_types", display_name="Export Types", show=False, info="Comma-separated types to export (e.g., tools,gateways)",tool_mode=True),
        DataInput(name="import_data", display_name="Import Data", show=False, info="JSON data to import",tool_mode=True),
        StrInput(name="conflict_strategy", display_name="Conflict Strategy", show=False, info="Strategy for handling conflicts (overwrite, skip, merge)",tool_mode=True),
        BoolInput(name="dry_run", display_name="Dry Run", show=False, info="Perform a dry run without actually importing",tool_mode=True),
        StrInput(name="agent_id", display_name="A2A Agent ID", show=False, info="The ID of the A2A agent",tool_mode=True),
        StrInput(name="agent_name", display_name="A2A Agent Name", show=False, info="The name of the A2A agent",tool_mode=True),
        StrInput(name="agent_type", display_name="Agent Type", show=False, info="Type of agent (e.g., openai, claude)",tool_mode=True),
        StrInput(name="endpoint_url", display_name="Endpoint URL", show=False, info="The endpoint URL for the agent",tool_mode=True),
        StrInput(name="agent_description", display_name="Agent Description", show=False, info="Description of the A2A agent",tool_mode=True),
        StrInput(name="auth_type", display_name="Auth Type", show=False, info="Authentication type (e.g., bearer, api_key)",tool_mode=True),
        StrInput(name="auth_value", display_name="Auth Value", show=False, info="Authentication value or environment variable name",tool_mode=True),
        StrInput(name="model", display_name="Model", show=False, info="Model name (e.g., gpt-4-turbo)",tool_mode=True),    
        MultilineInput(name="agent_message", display_name="Agent Message", show=False, info="Message to send to the A2A agent",tool_mode=True),
        MultilineInput(name="additional_config", display_name="Additional Config", show=False, info="Additional configuration as JSON",tool_mode=True),
    ]
    
    outputs = [
        # Server Health
        Output(name="check_server_health", display_name="Check Server Health", method="check_server_health"),
        Output(name="check_server_readiness", display_name="Check Server Readiness", method="check_server_readiness"),
        Output(name="check_server_version", display_name="Check Server Version", method="check_server_version"),
        # Gateway Management
        Output(name="list_gateways", display_name="List Gateways", method="list_gateways"),
        Output(name="get_gateway", display_name="Get Gateway", method="get_gateway"),
        Output(name="register_gateway", display_name="Register Gateway", method="register_gateway"),
        Output(name="update_gateway", display_name="Update Gateway", method="update_gateway"),
        Output(name="toggle_gateway", display_name="Toggle Gateway", method="toggle_gateway"),
        Output(name="delete_gateway", display_name="Delete Gateway", method="delete_gateway"),
        # Tool Management
        Output(name="list_tools", display_name="List Tools", method="list_tools"),
        Output(name="get_tool_details", display_name="Get Tool Details", method="get_tool_details"),
        Output(name="register_custom_tool", display_name="Register Custom Tool", method="register_custom_tool"),
        Output(name="invoke_tool", display_name="Invoke Tool", method="invoke_tool"),
        Output(name="update_tool", display_name="Update Tool", method="update_tool"),
        Output(name="toggle_tool", display_name="Toggle Tool", method="toggle_tool"),
        Output(name="delete_tool", display_name="Delete Tool", method="delete_tool"),
        # Virtual Server Management
        Output(name="list_virtual_servers", display_name="List Virtual Servers", method="list_virtual_servers"),
        Output(name="create_virtual_server", display_name="Create Virtual Server", method="create_virtual_server"),
        Output(name="get_virtual_server_details", display_name="Get Virtual Server Details", method="get_virtual_server_details"),
        Output(name="list_server_tools", display_name="List Server Tools", method="list_server_tools"),
        Output(name="list_server_resources", display_name="List Server Resources", method="list_server_resources"),
        Output(name="list_server_prompts", display_name="List Server Prompts", method="list_server_prompts"),
        # Resource Management
        Output(name="list_resources", display_name="List Resources", method="list_resources"),
        Output(name="register_resource", display_name="Register Resource", method="register_resource"),
        Output(name="get_resource_details", display_name="Get Resource Details", method="get_resource_details"),
        Output(name="read_resource_content", display_name="Read Resource Content", method="read_resource_content"),
        # Prompt Management
        Output(name="list_prompts", display_name="List Prompts", method="list_prompts"),
        Output(name="register_prompt", display_name="Register Prompt", method="register_prompt"),
        Output(name="get_prompt_details", display_name="Get Prompt Details", method="get_prompt_details"),
        Output(name="execute_prompt", display_name="Execute Prompt", method="execute_prompt"),
        Output(name="update_prompt", display_name="Update Prompt", method="update_prompt"),
        Output(name="toggle_prompt", display_name="Toggle Prompt", method="toggle_prompt"),
        Output(name="delete_prompt", display_name="Delete Prompt", method="delete_prompt"),
        # Tag Management
        Output(name="list_tags", display_name="List Tags", method="list_tags"),
        Output(name="get_tag_entities", display_name="Get Tag Entities", method="get_tag_entities"),
        # Bulk Operations
        Output(name="export_configuration", display_name="Export Configuration", method="export_configuration"),
        Output(name="import_configuration", display_name="Import Configuration", method="import_configuration"),
        # A2A Agent Management
        Output(name="list_a2a_agents", display_name="List A2A Agents", method="list_a2a_agents"),
        Output(name="register_a2a_agent", display_name="Register A2A Agent", method="register_a2a_agent"),
        Output(name="get_a2a_agent_details", display_name="Get A2A Agent Details", method="get_a2a_agent_details"),
        Output(name="invoke_a2a_agent", display_name="Invoke A2A Agent", method="invoke_a2a_agent"),
        Output(name="update_a2a_agent", display_name="Update A2A Agent", method="update_a2a_agent"),
        Output(name="delete_a2a_agent", display_name="Delete A2A Agent", method="delete_a2a_agent"),
    ]
    
    def _get_token_value(self):
        """Helper to extract token value from SecretStrInput."""
        token_value = self.token
        if hasattr(self.token, 'get_secret_value'):
            token_value = self.token.get_secret_value()
        elif isinstance(self.token, str):
            token_value = self.token
        return token_value
    
    def _execute_curl(self, curl_command, timeout=10):
        """Helper to execute curl command and return result."""
        try:
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                return Data(
                    value={
                        "status": "error",
                        "message": f"Curl command failed with return code {result.returncode}",
                        "error": result.stderr,
                        "raw_response": result.stdout
                    }
                )
            
            # Try to parse JSON response
            try:
                response_data = json.loads(result.stdout)
                return Data(
                    value={
                        "status": "success",
                        "data": response_data,
                        "raw_response": result.stdout
                    }
                )
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response
                return Data(
                    value={
                        "status": "success",
                        "message": "Server responded but response is not valid JSON",
                        "raw_response": result.stdout
                    }
                )
                
        except subprocess.TimeoutExpired:
            return Data(
                value={
                    "status": "error",
                    "message": f"Request timed out after {timeout} seconds"
                }
            )
        except FileNotFoundError:
            return Data(
                value={
                    "status": "error",
                    "message": "curl command not found. Please ensure curl is installed and available in PATH"
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}"
                }
            )
    
    # Server Health Methods
    def check_server_health(self) -> Data:
        """Check server health."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        curl_command = ["curl", "-s", f"{base_url}/health"]
        return self._execute_curl(curl_command)
    
    def check_server_readiness(self) -> Data:
        """Check server readiness."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/ready"]
        return self._execute_curl(curl_command)
    
    def check_server_version(self) -> Data:
        """Check server version."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/version"]
        return self._execute_curl(curl_command)
    
    # Gateway Management Methods
    def list_gateways(self) -> Data:
        """List all gateways."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/gateways"]
        return self._execute_curl(curl_command)
    
    def get_gateway(self) -> Data:
        """Get gateway details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        gateway_id = getattr(self, 'gateway_id', None)
        if not gateway_id:
            return Data(value={"status": "error", "message": "Gateway ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/gateways/{gateway_id}"]
        return self._execute_curl(curl_command)
    
    def register_gateway(self) -> Data:
        """Register a new gateway."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        gateway_name = getattr(self, 'gateway_name', None)
        gateway_url = getattr(self, 'gateway_url', None)
        transport = getattr(self, 'transport', None)
        description = getattr(self, 'gateway_description', None)
        
        if not gateway_name or not gateway_url or not transport:
            return Data(value={"status": "error", "message": "Gateway name, URL, and transport are required"})
        
        payload = {
            "name": gateway_name,
            "url": gateway_url,
            "transport": transport
        }
        if description:
            payload["description"] = description
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/gateways"
        ]
        return self._execute_curl(curl_command)
    
    def update_gateway(self) -> Data:
        """Update gateway properties."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        gateway_id = getattr(self, 'gateway_id', None)
        if not gateway_id:
            return Data(value={"status": "error", "message": "Gateway ID is required"})
        
        payload = {}
        if hasattr(self, 'gateway_name') and self.gateway_name:
            payload["name"] = self.gateway_name
        if hasattr(self, 'gateway_description') and self.gateway_description:
            payload["description"] = self.gateway_description
        if hasattr(self, 'gateway_enabled') and self.gateway_enabled is not None:
            payload["enabled"] = self.gateway_enabled
        
        if not payload:
            return Data(value={"status": "error", "message": "At least one field to update is required"})
        
        curl_command = [
            "curl", "-s", "-X", "PUT",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/gateways/{gateway_id}"
        ]
        return self._execute_curl(curl_command)
    
    def toggle_gateway(self) -> Data:
        """Toggle gateway enabled status."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        gateway_id = getattr(self, 'gateway_id', None)
        activate = getattr(self, 'activate', True)
        if not gateway_id:
            return Data(value={"status": "error", "message": "Gateway ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/gateways/{gateway_id}/toggle?activate={'true' if activate else 'false'}"
        ]
        return self._execute_curl(curl_command)
    
    def delete_gateway(self) -> Data:
        """Delete a gateway."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        gateway_id = getattr(self, 'gateway_id', None)
        if not gateway_id:
            return Data(value={"status": "error", "message": "Gateway ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "DELETE",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/gateways/{gateway_id}"
        ]
        return self._execute_curl(curl_command)
    
    # Tool Management Methods
    def list_tools(self) -> Data:
        """List all tools."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tools"]
        return self._execute_curl(curl_command)
    
    def get_tool_details(self) -> Data:
        """Get tool details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_id = getattr(self, 'tool_id', None)
        if not tool_id:
            return Data(value={"status": "error", "message": "Tool ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tools/{tool_id}"]
        return self._execute_curl(curl_command)
    
    def register_custom_tool(self) -> Data:
        """Register a custom tool."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_name = getattr(self, 'tool_name', None)
        tool_description = getattr(self, 'tool_description', None)
        tool_url = getattr(self, 'tool_url', None)
        integration_type = getattr(self, 'integration_type', None)
        request_type = getattr(self, 'request_type', None)
        input_schema_str = getattr(self, 'input_schema', None)
        
        if not all([tool_name, tool_description, tool_url, integration_type, request_type, input_schema_str]):
            return Data(value={"status": "error", "message": "All tool fields are required"})
        
        try:
            input_schema = json.loads(input_schema_str)
        except json.JSONDecodeError as e:
            return Data(value={"status": "error", "message": f"Invalid JSON in input schema: {str(e)}"})
        
        payload = {
            "tool": {
                "name": tool_name,
                "description": tool_description,
                "url": tool_url,
                "integration_type": integration_type,
                "request_type": request_type,
                "input_schema": input_schema
            }
        }
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/tools"
        ]
        return self._execute_curl(curl_command)
    
    def invoke_tool(self) -> Data:
        """Invoke a tool."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_name = getattr(self, 'tool_name', None)
        tool_arguments_str = getattr(self, 'tool_arguments', None)
        
        if not tool_name or not tool_arguments_str:
            return Data(value={"status": "error", "message": "Tool name and arguments are required"})
        
        try:
            args = json.loads(tool_arguments_str)
        except json.JSONDecodeError as e:
            return Data(value={"status": "error", "message": f"Invalid JSON in arguments: {str(e)}"})
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/rpc"
        ]
        return self._execute_curl(curl_command, timeout=30)
    
    def update_tool(self) -> Data:
        """Update tool properties."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_id = getattr(self, 'tool_id', None)
        if not tool_id:
            return Data(value={"status": "error", "message": "Tool ID is required"})
        
        payload = {}
        if hasattr(self, 'tool_description') and self.tool_description:
            payload["description"] = self.tool_description
        if hasattr(self, 'tool_enabled') and self.tool_enabled is not None:
            payload["enabled"] = self.tool_enabled
        
        if not payload:
            return Data(value={"status": "error", "message": "At least one field to update is required"})
        
        curl_command = [
            "curl", "-s", "-X", "PUT",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/tools/{tool_id}"
        ]
        return self._execute_curl(curl_command)
    
    def toggle_tool(self) -> Data:
        """Toggle tool enabled status."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_id = getattr(self, 'tool_id', None)
        activate = getattr(self, 'activate', True)
        if not tool_id:
            return Data(value={"status": "error", "message": "Tool ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/tools/{tool_id}/toggle?activate={'true' if activate else 'false'}"
        ]
        return self._execute_curl(curl_command)
    
    def delete_tool(self) -> Data:
        """Delete a tool."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tool_id = getattr(self, 'tool_id', None)
        if not tool_id:
            return Data(value={"status": "error", "message": "Tool ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "DELETE",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/tools/{tool_id}"
        ]
        return self._execute_curl(curl_command)
    
    # Virtual Server Management Methods
    def list_virtual_servers(self) -> Data:
        """List all virtual servers."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers"]
        return self._execute_curl(curl_command)
    
    def create_virtual_server(self) -> Data:
        """Create a virtual server."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        server_name = getattr(self, 'server_name', None)
        server_description = getattr(self, 'server_description', None)
        associated_tools_str = getattr(self, 'associated_tools', None)
        
        if not server_name:
            return Data(value={"status": "error", "message": "Server name is required"})
        
        payload = {"name": server_name}
        if server_description:
            payload["description"] = server_description
        if associated_tools_str:
            try:
                payload["associated_tools"] = json.loads(associated_tools_str)
            except json.JSONDecodeError:
                return Data(value={"status": "error", "message": "Invalid JSON in associated tools"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/servers"
        ]
        return self._execute_curl(curl_command)
    
    def get_virtual_server_details(self) -> Data:
        """Get virtual server details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}"]
        return self._execute_curl(curl_command)
    
    def list_server_tools(self) -> Data:
        """List server tools."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/tools"]
        return self._execute_curl(curl_command)
    
    def list_server_resources(self) -> Data:
        """List server resources."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/resources"]
        return self._execute_curl(curl_command)
    
    def list_server_prompts(self) -> Data:
        """List server prompts."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/prompts"]
        return self._execute_curl(curl_command)
    
    # Resource Management Methods
    def list_resources(self) -> Data:
        """List all resources."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources"]
        return self._execute_curl(curl_command)
    
    def register_resource(self) -> Data:
        """Register a resource."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        resource_name = getattr(self, 'resource_name', None)
        resource_uri = getattr(self, 'resource_uri', None)
        resource_description = getattr(self, 'resource_description', None)
        mime_type = getattr(self, 'mime_type', None)
        resource_content = getattr(self, 'resource_content', None)
        
        if not resource_name or not resource_uri:
            return Data(value={"status": "error", "message": "Resource name and URI are required"})
        
        payload = {
            "name": resource_name,
            "uri": resource_uri
        }
        if resource_description:
            payload["description"] = resource_description
        if mime_type:
            payload["mime_type"] = mime_type
        if resource_content:
            payload["content"] = resource_content
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/resources"
        ]
        return self._execute_curl(curl_command)
    
    def get_resource_details(self) -> Data:
        """Get resource details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        resource_uri = getattr(self, 'resource_uri', None)
        if not resource_uri:
            return Data(value={"status": "error", "message": "Resource URI is required"})
        encoded_uri = quote(resource_uri, safe='')
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources/{encoded_uri}"]
        return self._execute_curl(curl_command)
    
    def read_resource_content(self) -> Data:
        """Read resource content."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        resource_uri = getattr(self, 'resource_uri', None)
        if not resource_uri:
            return Data(value={"status": "error", "message": "Resource URI is required"})
        encoded_uri = quote(resource_uri, safe='')
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources/{encoded_uri}/read"]
        return self._execute_curl(curl_command)
    
    # Prompt Management Methods
    def list_prompts(self) -> Data:
        """List all prompts."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/prompts"]
        return self._execute_curl(curl_command)
    
    def register_prompt(self) -> Data:
        """Register a prompt."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_name = getattr(self, 'prompt_name', None)
        template = getattr(self, 'template', None)
        prompt_description = getattr(self, 'prompt_description', None)
        prompt_arguments_str = getattr(self, 'prompt_arguments', None)
        
        if not prompt_name or not template:
            return Data(value={"status": "error", "message": "Prompt name and template are required"})
        
        payload = {
            "name": prompt_name,
            "template": template
        }
        if prompt_description:
            payload["description"] = prompt_description
        if prompt_arguments_str:
            try:
                payload["arguments"] = json.loads(prompt_arguments_str)
            except json.JSONDecodeError:
                return Data(value={"status": "error", "message": "Invalid JSON in prompt arguments"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/prompts"
        ]
        return self._execute_curl(curl_command)
    
    def get_prompt_details(self) -> Data:
        """Get prompt details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/prompts/{prompt_id}"]
        return self._execute_curl(curl_command)
    
    def execute_prompt(self) -> Data:
        """Execute a prompt."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        prompt_arguments_str = getattr(self, 'prompt_arguments', None)
        
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        
        payload = {}
        if prompt_arguments_str:
            try:
                payload["arguments"] = json.loads(prompt_arguments_str)
            except json.JSONDecodeError as e:
                return Data(value={"status": "error", "message": f"Invalid JSON in prompt arguments: {str(e)}"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/prompts/{prompt_id}"
        ]
        return self._execute_curl(curl_command)
    
    def update_prompt(self) -> Data:
        """Update a prompt."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        
        payload = {}
        if hasattr(self, 'prompt_description') and self.prompt_description:
            payload["description"] = self.prompt_description
        if hasattr(self, 'template') and self.template:
            payload["template"] = self.template
        
        if not payload:
            return Data(value={"status": "error", "message": "At least one field to update is required"})
        
        curl_command = [
            "curl", "-s", "-X", "PUT",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/prompts/{prompt_id}"
        ]
        return self._execute_curl(curl_command)
    
    def toggle_prompt(self) -> Data:
        """Toggle prompt enabled status."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        activate = getattr(self, 'activate', True)
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/prompts/{prompt_id}/toggle?activate={'true' if activate else 'false'}"
        ]
        return self._execute_curl(curl_command)
    
    def delete_prompt(self) -> Data:
        """Delete a prompt."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "DELETE",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/prompts/{prompt_id}"
        ]
        return self._execute_curl(curl_command)
    
    # Tag Management Methods
    def list_tags(self) -> Data:
        """List all tags."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        entity_types = getattr(self, 'entity_types', 'gateways,servers,tools,resources,prompts')
        include_entities = getattr(self, 'include_entities', False)
        
        encoded_entity_types = quote(entity_types, safe='')
        curl_command = [
            "curl", "-s", "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/tags?entity_types={encoded_entity_types}&include_entities={'true' if include_entities else 'false'}"
        ]
        return self._execute_curl(curl_command)
    
    def get_tag_entities(self) -> Data:
        """Get tag entities."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        tag_name = getattr(self, 'tag_name', None)
        if not tag_name:
            return Data(value={"status": "error", "message": "Tag name is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tags/{tag_name}/entities"]
        return self._execute_curl(curl_command)
    
    # Bulk Operations Methods
    def export_configuration(self) -> Data:
        """Export configuration."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        export_types = getattr(self, 'export_types', None)
        
        url = f"{base_url}/export"
        if export_types:
            encoded_types = quote(export_types, safe='')
            url = f"{url}?types={encoded_types}"
        
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", url]
        return self._execute_curl(curl_command)
    
    def import_configuration(self) -> Data:
        """Import configuration."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        import_data_obj = getattr(self, 'import_data', None)
        conflict_strategy = getattr(self, 'conflict_strategy', 'merge')
        dry_run = getattr(self, 'dry_run', False)
        
        if not import_data_obj:
            return Data(value={"status": "error", "message": "Import data is required"})
        
        # Handle DataInput
        if hasattr(import_data_obj, 'data'):
            import_data = import_data_obj.data
        elif hasattr(import_data_obj, 'value'):
            import_data = import_data_obj.value
        else:
            import_data = import_data_obj
        
        # Convert to JSON if needed
        if isinstance(import_data, str):
            try:
                import_data = json.loads(import_data)
            except json.JSONDecodeError:
                return Data(value={"status": "error", "message": "Invalid JSON in import data"})
        
        payload = {
            "data": import_data,
            "conflict_strategy": conflict_strategy,
            "dry_run": dry_run
        }
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/import"
        ]
        return self._execute_curl(curl_command)
    
    # A2A Agent Management Methods
    def list_a2a_agents(self) -> Data:
        """List all A2A agents."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/a2a"]
        return self._execute_curl(curl_command)
    
    def register_a2a_agent(self) -> Data:
        """Register an A2A agent."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        agent_name = getattr(self, 'agent_name', None)
        agent_type = getattr(self, 'agent_type', None)
        endpoint_url = getattr(self, 'endpoint_url', None)
        agent_description = getattr(self, 'agent_description', None)
        auth_type = getattr(self, 'auth_type', None)
        auth_value = getattr(self, 'auth_value', None)
        
        if not agent_name or not agent_type or not endpoint_url:
            return Data(value={"status": "error", "message": "Agent name, type, and endpoint URL are required"})
        
        agent_data = {
            "name": agent_name,
            "agent_type": agent_type,
            "endpoint_url": endpoint_url
        }
        if agent_description:
            agent_data["description"] = agent_description
        if auth_type:
            agent_data["auth_type"] = auth_type
        if auth_value:
            agent_data["auth_value"] = auth_value
        
        payload = {"agent": agent_data}
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/a2a"
        ]
        return self._execute_curl(curl_command)
    
    def get_a2a_agent_details(self) -> Data:
        """Get A2A agent details."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        agent_id = getattr(self, 'agent_id', None)
        if not agent_id:
            return Data(value={"status": "error", "message": "Agent ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/a2a/{agent_id}"]
        return self._execute_curl(curl_command)
    
    def invoke_a2a_agent(self) -> Data:
        """Invoke an A2A agent."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        agent_name = getattr(self, 'agent_name', None)
        agent_message = getattr(self, 'agent_message', None)
        
        if not agent_name or not agent_message:
            return Data(value={"status": "error", "message": "Agent name and message are required"})
        
        payload = {"message": agent_message}
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/a2a/{agent_name}/invoke"
        ]
        return self._execute_curl(curl_command, timeout=30)
    
    def update_a2a_agent(self) -> Data:
        """Update an A2A agent."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        agent_id = getattr(self, 'agent_id', None)
        if not agent_id:
            return Data(value={"status": "error", "message": "Agent ID is required"})
        
        payload = {}
        if hasattr(self, 'model') and self.model:
            payload["model"] = self.model
        if hasattr(self, 'agent_description') and self.agent_description:
            payload["description"] = self.agent_description
        
        additional_config_str = getattr(self, 'additional_config', None)
        if additional_config_str:
            try:
                additional_config = json.loads(additional_config_str)
                payload.update(additional_config)
            except json.JSONDecodeError:
                return Data(value={"status": "error", "message": "Invalid JSON in additional config"})
        
        if not payload:
            return Data(value={"status": "error", "message": "At least one field to update is required"})
        
        curl_command = [
            "curl", "-s", "-X", "PUT",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/a2a/{agent_id}"
        ]
        return self._execute_curl(curl_command)
    
    def delete_a2a_agent(self) -> Data:
        """Delete an A2A agent."""
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        token_value = self._get_token_value()
        agent_id = getattr(self, 'agent_id', None)
        if not agent_id:
            return Data(value={"status": "error", "message": "Agent ID is required"})
        
        curl_command = [
            "curl", "-s", "-X", "DELETE",
            "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/a2a/{agent_id}"
        ]
        return self._execute_curl(curl_command)