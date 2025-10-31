"""
MCP Context Forge All-in-One Component

This component consolidates all MCP Context Forge actions into a single unified interface.
Select an action from the dropdown to perform operations on the MCP Context Forge server.
"""

import subprocess
import json
from typing import Optional
from urllib.parse import quote

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, MultilineInput, BoolInput, IntInput, DataInput
from langflow.inputs import SortableListInput
from langflow.schema import Data

class MCPContextForgeAllComponent(Component):
    display_name = "MCP Context Forge"
    description = "Unified component for all MCP Context Forge operations. Select an action to perform operations on the MCP Context Forge server."
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
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="Select the MCP Context Forge action to perform",
            tool_mode=True,
            options=[
                # Server Health
                {"name": "Check Server Health", "icon": "heart"},
                {"name": "Check Server Readiness", "icon": "check-circle"},
                {"name": "Check Server Version", "icon": "info"},
                # Gateway Management
                {"name": "List Gateways", "icon": "list"},
                {"name": "Get Gateway", "icon": "search"},
                {"name": "Register Gateway", "icon": "plus"},
                {"name": "Update Gateway", "icon": "edit"},
                {"name": "Toggle Gateway", "icon": "toggle-right"},
                {"name": "Delete Gateway", "icon": "trash"},
                # Tool Management
                {"name": "List Tools", "icon": "wrench"},
                {"name": "Get Tool Details", "icon": "info"},
                {"name": "Register Tool", "icon": "plus-circle"},
                {"name": "Register Custom Tool", "icon": "plus-circle"},
                {"name": "Invoke Tool", "icon": "play"},
                {"name": "Update Tool", "icon": "edit"},
                {"name": "Toggle Tool", "icon": "toggle-right"},
                {"name": "Delete Tool", "icon": "trash"},
                # Virtual Server Management
                {"name": "List Virtual Servers", "icon": "server"},
                {"name": "Create Virtual Server", "icon": "plus-circle"},
                {"name": "Get Virtual Server Details", "icon": "info"},
                {"name": "List Server Tools", "icon": "wrench"},
                {"name": "List Server Resources", "icon": "file-text"},
                {"name": "List Server Prompts", "icon": "message-square"},
                # Resource Management
                {"name": "List Resources", "icon": "file-text"},
                {"name": "Register Resource", "icon": "plus-circle"},
                {"name": "Get Resource Details", "icon": "info"},
                {"name": "Read Resource Content", "icon": "file-text"},
                # Prompt Management
                {"name": "List Prompts", "icon": "message-square"},
                {"name": "Register Prompt", "icon": "plus-circle"},
                {"name": "Get Prompt Details", "icon": "info"},
                {"name": "Execute Prompt", "icon": "play"},
                {"name": "Update Prompt", "icon": "edit"},
                {"name": "Toggle Prompt", "icon": "toggle-right"},
                {"name": "Delete Prompt", "icon": "trash"},
                # Tag Management
                {"name": "List Tags", "icon": "tag"},
                {"name": "Get Tag Entities", "icon": "list"},
                # Bulk Operations
                {"name": "Export Configuration", "icon": "download"},
                {"name": "Import Configuration", "icon": "upload"},
                # A2A Agent Management
                {"name": "List A2A Agents", "icon": "users"},
                {"name": "Register A2A Agent", "icon": "plus-circle"},
                {"name": "Get A2A Agent Details", "icon": "info"},
                {"name": "Invoke A2A Agent", "icon": "play"},
                {"name": "Update A2A Agent", "icon": "edit"},
                {"name": "Delete A2A Agent", "icon": "trash"},
            ],
            real_time_refresh=True,
            limit=1,

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
        Output(name="mcp_result", display_name="Result", method="run_action")
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
    
    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config
        
        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []
        
        # Map each action to its required fields
        field_map = {
            # Server Health
            "Check Server Health": ["base_url"],
            "Check Server Readiness": ["base_url", "token"],
            "Check Server Version": ["base_url", "token"],
            # Gateway Management
            "List Gateways": ["base_url", "token"],
            "Get Gateway": ["base_url", "token", "gateway_id"],
            "Register Gateway": ["base_url", "token", "gateway_name", "gateway_url", "transport"],
            "Update Gateway": ["base_url", "token", "gateway_id"],
            "Toggle Gateway": ["base_url", "token", "gateway_id", "activate"],
            "Delete Gateway": ["base_url", "token", "gateway_id"],
            # Tool Management
            "List Tools": ["base_url", "token"],
            "Get Tool Details": ["base_url", "token", "tool_id"],
            "Register Tool": ["base_url", "token", "tool_name", "tool_url"],
            "Register Custom Tool": ["base_url", "token", "tool_name", "tool_description", "tool_url", "integration_type", "request_type", "input_schema"],
            "Invoke Tool": ["base_url", "token", "tool_name", "tool_arguments"],
            "Update Tool": ["base_url", "token", "tool_id"],
            "Toggle Tool": ["base_url", "token", "tool_id", "activate"],
            "Delete Tool": ["base_url", "token", "tool_id"],
            # Virtual Server Management
            "List Virtual Servers": ["base_url", "token"],
            "Create Virtual Server": ["base_url", "token", "server_name"],
            "Get Virtual Server Details": ["base_url", "token", "server_id"],
            "List Server Tools": ["base_url", "token", "server_id"],
            "List Server Resources": ["base_url", "token", "server_id"],
            "List Server Prompts": ["base_url", "token", "server_id"],
            # Resource Management
            "List Resources": ["base_url", "token"],
            "Register Resource": ["base_url", "token", "resource_name", "resource_uri"],
            "Get Resource Details": ["base_url", "token", "resource_uri"],
            "Read Resource Content": ["base_url", "token", "resource_uri"],
            # Prompt Management
            "List Prompts": ["base_url", "token"],
            "Register Prompt": ["base_url", "token", "prompt_name", "template"],
            "Get Prompt Details": ["base_url", "token", "prompt_id"],
            "Execute Prompt": ["base_url", "token", "prompt_id", "prompt_arguments"],
            "Update Prompt": ["base_url", "token", "prompt_id"],
            "Toggle Prompt": ["base_url", "token", "prompt_id", "activate"],
            "Delete Prompt": ["base_url", "token", "prompt_id"],
            # Tag Management
            "List Tags": ["base_url", "token"],
            "Get Tag Entities": ["base_url", "token", "tag_name"],
            # Bulk Operations
            "Export Configuration": ["base_url", "token"],
            "Import Configuration": ["base_url", "token", "import_data"],
            # A2A Agent Management
            "List A2A Agents": ["base_url", "token"],
            "Register A2A Agent": ["base_url", "token", "agent_name", "agent_type", "endpoint_url"],
            "Get A2A Agent Details": ["base_url", "token", "agent_id"],
            "Invoke A2A Agent": ["base_url", "token", "agent_name", "agent_message"],
            "Update A2A Agent": ["base_url", "token", "agent_id"],
            "Delete A2A Agent": ["base_url", "token", "agent_id"],
        }
        
        # Hide all dynamic fields first
        all_fields = [
            "gateway_id", "gateway_name", "gateway_url", "gateway_description", "transport", 
            "gateway_enabled", "activate", "tool_id", "tool_name", "tool_description", 
            "tool_url", "integration_type", "request_type", "input_schema", "tool_arguments",
            "tool_enabled", "server_id", "server_name", "server_description", "associated_tools",
            "resource_uri", "resource_name", "resource_description", "mime_type", "resource_content",
            "prompt_id", "prompt_name", "prompt_description", "template", "prompt_arguments",
            "prompt_enabled", "tag_name", "entity_types", "include_entities", "export_types",
            "import_data", "conflict_str tengo", "dry_run", "agent_id", "agent_name", "agent_type",
            "endpoint_url", "agent_description", "auth_type", "auth_value", "model", 
            "agent_message", "additional_config"
        ]
        
        for field_name in all_fields:
            if field_name in build_config:
                build_config[field_name]["show"] = False
        
        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True
        
        return build_config
    
    def run_action(self) -> Data:
        """Execute the selected MCP Context Forge action."""
        if not hasattr(self, 'action') or not self.action:
            return Data(value={"status": "error", "message": "Action is required"})
        
        # Extract action name
        action_name = None
        if isinstance(self.action, list) and len(self.action) > 0:
            action_name = self.action[0].get("name")
        elif isinstance(self.action, dict):
            action_name = self.action.get("name")
        
        if not action_name:
            return Data(value={"status": "error", "message": "Invalid action selected"})
        
        base_url = getattr(self, 'base_url', 'http://localhost:4444').rstrip('/')
        
        # Handle each action type
        if action_name == "Check Server Health":
            return self._check_server_health(base_url)
        elif action_name == "Check Server Readiness":
            return self._check_server_readiness(base_url)
        elif action_name == "Check Server Version":
            return self._check_server_version(base_url)
        elif action_name == "List Gateways":
            return self._list_gateways(base_url)
        elif action_name == "Get Gateway":
            return self._get_gateway(base_url)
        elif action_name == "Register Gateway":
            return self._register_gateway(base_url)
        elif action_name == "Update Gateway":
            return self._update_gateway(base_url)
        elif action_name == "Toggle Gateway":
            return self._toggle_gateway(base_url)
        elif action_name == "Delete Gateway":
            return self._delete_gateway(base_url)
        elif action_name == "List Tools":
            return self._list_tools(base_url)
        elif action_name == "Get Tool Details":
            return self._get_tool_details(base_url)
        elif action_name == "Register Tool":
            return self._register_tool(base_url)
        elif action_name == "Register Custom Tool":
            return self._register_custom_tool(base_url)
        elif action_name == "Invoke Tool":
            return self._invoke_tool(base_url)
        elif action_name == "Update Tool":
            return self._update_tool(base_url)
        elif action_name == "Toggle Tool":
            return self._toggle_tool(base_url)
        elif action_name == "Delete Tool":
            return self._delete_tool(base_url)
        elif action_name == "List Virtual Servers":
            return self._list_virtual_servers(base_url)
        elif action_name == "Create Virtual Server":
            return self._create_virtual_server(base_url)
        elif action_name == "Get Virtual Server Details":
            return self._get_virtual_server_details(base_url)
        elif action_name == "List Server Tools":
            return self._list_server_tools(base_url)
        elif action_name == "List Server Resources":
            return self._list_server_resources(base_url)
        elif action_name == "List Server Prompts":
            return self._list_server_prompts(base_url)
        elif action_name == "List Resources":
            return self._list_resources(base_url)
        elif action_name == "Register Resource":
            return self._register_resource(base_url)
        elif action_name == "Get Resource Details":
            return self._get_resource_details(base_url)
        elif action_name == "Read Resource Content":
            return self._read_resource_content(base_url)
        elif action_name == "List Prompts":
            return self._list_prompts(base_url)
        elif action_name == "Register Prompt":
            return self._register_prompt(base_url)
        elif action_name == "Get Prompt Details":
            return self._get_prompt_details(base_url)
        elif action_name == "Execute Prompt":
            return self._execute_prompt(base_url)
        elif action_name == "Update Prompt":
            return self._update_prompt(base_url)
        elif action_name == "Toggle Prompt":
            return self._toggle_prompt(base_url)
        elif action_name == "Delete Prompt":
            return self._delete_prompt(base_url)
        elif action_name == "List Tags":
            return self._list_tags(base_url)
        elif action_name == "Get Tag Entities":
            return self._get_tag_entities(base_url)
        elif action_name == "Export Configuration":
            return self._export_configuration(base_url)
        elif action_name == "Import Configuration":
            return self._import_configuration(base_url)
        elif action_name == "List A2A Agents":
            return self._list_a2a_agents(base_url)
        elif action_name == "Register A2A Agent":
            return self._register_a2a_agent(base_url)
        elif action_name == "Get A2A Agent Details":
            return self._get_a2a_agent_details(base_url)
        elif action_name == "Invoke A2A Agent":
            return self._invoke_a2a_agent(base_url)
        elif action_name == "Update A2A Agent":
            return self._update_a2a_agent(base_url)
        elif action_name == "Delete A2A Agent":
            return self._delete_a2a_agent(base_url)
        else:
            return Data(value={"status": "error", "message": f"Unknown action: {action_name}"})
    
    # Server Health Methods
    def _check_server_health(self, base_url):
        """Check server health."""
        curl_command = ["curl", "-s", f"{base_url}/health"]
        return self._execute_curl(curl_command)
    
    def _check_server_readiness(self, base_url):
        """Check server readiness."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/ready"]
        return self._execute_curl(curl_command)
    
    def _check_server_version(self, base_url):
        """Check server version."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/version"]
        return self._execute_curl(curl_command)
    
    # Gateway Management Methods
    def _list_gateways(self, base_url):
        """List all gateways."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/gateways"]
        return self._execute_curl(curl_command)
    
    def _get_gateway(self, base_url):
        """Get gateway details."""
        token_value = self._get_token_value()
        gateway_id = getattr(self, 'gateway_id', None)
        if not gateway_id:
            return Data(value={"status": "error", "message": "Gateway ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/gateways/{gateway_id}"]
        return self._execute_curl(curl_command)
    
    def _register_gateway(self, base_url):
        """Register a new gateway."""
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
    
    def _update_gateway(self, base_url):
        """Update gateway properties."""
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
    
    def _toggle_gateway(self, base_url):
        """Toggle gateway enabled status."""
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
    
    def _delete_gateway(self, base_url):
        """Delete a gateway."""
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
    def _list_tools(self, base_url):
        """List all tools."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tools"]
        return self._execute_curl(curl_command)
    
    def _get_tool_details(self, base_url):
        """Get tool details."""
        token_value = self._get_token_value()
        tool_id = getattr(self, 'tool_id', None)
        if not tool_id:
            return Data(value={"status": "error", "message": "Tool ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tools/{tool_id}"]
        return self._execute_curl(curl_command)
    
    def _register_tool(self, base_url):
        """Register a new tool (simplified format)."""
        token_value = self._get_token_value()
        tool_name = getattr(self, 'tool_name', None)
        tool_url = getattr(self, 'tool_url', None)
        tool_description = getattr(self, 'tool_description', None)
        input_schema_str = getattr(self, 'input_schema', None)
        
        if not tool_name or not tool_url:
            return Data(value={"status": "error", "message": "Tool name and URL are required"})
        
        payload = {
            "name": tool_name,
            "url": tool_url
        }
        
        if tool_description:
            payload["description"] = tool_description
        
        if input_schema_str:
            try:
                if isinstance(input_schema_str, str):
                    payload["input_schema"] = json.loads(input_schema_str)
                elif isinstance(input_schema_str, dict):
                    payload["input_schema"] = input_schema_str
                else:
                    payload["input_schema"] = input_schema_str
            except json.JSONDecodeError as e:
                return Data(value={"status": "error", "message": f"Invalid JSON in input_schema: {str(e)}"})
        
        curl_command = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: Bearer {token_value}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{base_url}/tools"
        ]
        return self._execute_curl(curl_command)
    
    def _register_custom_tool(self, base_url):
        """Register a custom tool."""
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
    
    def _invoke_tool(self, base_url):
        """Invoke a tool."""
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
    
    def _update_tool(self, base_url):
        """Update tool properties."""
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
    
    def _toggle_tool(self, base_url):
        """Toggle tool enabled status."""
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
    
    def _delete_tool(self, base_url):
        """Delete a tool."""
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
    def _list_virtual_servers(self, base_url):
        """List all virtual servers."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers"]
        return self._execute_curl(curl_command)
    
    def _create_virtual_server(self, base_url):
        """Create a virtual server."""
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
    
    def _get_virtual_server_details(self, base_url):
        """Get virtual server details."""
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}"]
        return self._execute_curl(curl_command)
    
    def _list_server_tools(self, base_url):
        """List server tools."""
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/tools"]
        return self._execute_curl(curl_command)
    
    def _list_server_resources(self, base_url):
        """List server resources."""
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/resources"]
        return self._execute_curl(curl_command)
    
    def _list_server_prompts(self, base_url):
        """List server prompts."""
        token_value = self._get_token_value()
        server_id = getattr(self, 'server_id', None)
        if not server_id:
            return Data(value={"status": "error", "message": "Server ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/servers/{server_id}/prompts"]
        return self._execute_curl(curl_command)
    
    # Resource Management Methods
    def _list_resources(self, base_url):
        """List all resources."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources"]
        return self._execute_curl(curl_command)
    
    def _register_resource(self, base_url):
        """Register a resource."""
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
    
    def _get_resource_details(self, base_url):
        """Get resource details."""
        token_value = self._get_token_value()
        resource_uri = getattr(self, 'resource_uri', None)
        if not resource_uri:
            return Data(value={"status": "error", "message": "Resource URI is required"})
        encoded_uri = quote(resource_uri, safe='')
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources/{encoded_uri}"]
        return self._execute_curl(curl_command)
    
    def _read_resource_content(self, base_url):
        """Read resource content."""
        token_value = self._get_token_value()
        resource_uri = getattr(self, 'resource_uri', None)
        if not resource_uri:
            return Data(value={"status": "error", "message": "Resource URI is required"})
        encoded_uri = quote(resource_uri, safe='')
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/resources/{encoded_uri}/read"]
        return self._execute_curl(curl_command)
    
    # Prompt Management Methods
    def _list_prompts(self, base_url):
        """List all prompts."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/prompts"]
        return self._execute_curl(curl_command)
    
    def _register_prompt(self, base_url):
        """Register a prompt."""
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
    
    def _get_prompt_details(self, base_url):
        """Get prompt details."""
        token_value = self._get_token_value()
        prompt_id = getattr(self, 'prompt_id', None)
        if not prompt_id:
            return Data(value={"status": "error", "message": "Prompt ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/prompts/{prompt_id}"]
        return self._execute_curl(curl_command)
    
    def _execute_prompt(self, base_url):
        """Execute a prompt."""
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
    
    def _update_prompt(self, base_url):
        """Update a prompt."""
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
    
    def _toggle_prompt(self, base_url):
        """Toggle prompt enabled status."""
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
    
    def _delete_prompt(self, base_url):
        """Delete a prompt."""
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
    def _list_tags(self, base_url):
        """List all tags."""
        token_value = self._get_token_value()
        entity_types = getattr(self, 'entity_types', 'gateways,servers,tools,resources,prompts')
        include_entities = getattr(self, 'include_entities', False)
        
        encoded_entity_types = quote(entity_types, safe='')
        curl_command = [
            "curl", "-s", "-H", f"Authorization: Bearer {token_value}",
            f"{base_url}/tags?entity_types={encoded_entity_types}&include_entities={'true' if include_entities else 'false'}"
        ]
        return self._execute_curl(curl_command)
    
    def _get_tag_entities(self, base_url):
        """Get tag entities."""
        token_value = self._get_token_value()
        tag_name = getattr(self, 'tag_name', None)
        if not tag_name:
            return Data(value={"status": "error", "message": "Tag name is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/tags/{tag_name}/entities"]
        return self._execute_curl(curl_command)
    
    # Bulk Operations Methods
    def _export_configuration(self, base_url):
        """Export configuration."""
        token_value = self._get_token_value()
        export_types = getattr(self, 'export_types', None)
        
        url = f"{base_url}/export"
        if export_types:
            encoded_types = quote(export_types, safe='')
            url = f"{url}?types={encoded_types}"
        
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", url]
        return self._execute_curl(curl_command)
    
    def _import_configuration(self, base_url):
        """Import configuration."""
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
    def _list_a2a_agents(self, base_url):
        """List all A2A agents."""
        token_value = self._get_token_value()
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/a2a"]
        return self._execute_curl(curl_command)
    
    def _register_a2a_agent(self, base_url):
        """Register an A2A agent."""
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
    
    def _get_a2a_agent_details(self, base_url):
        """Get A2A agent details."""
        token_value = self._get_token_value()
        agent_id = getattr(self, 'agent_id', None)
        if not agent_id:
            return Data(value={"status": "error", "message": "Agent ID is required"})
        curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token_value}", f"{base_url}/a2a/{agent_id}"]
        return self._execute_curl(curl_command)
    
    def _invoke_a2a_agent(self, base_url):
        """Invoke an A2A agent."""
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
    
    def _update_a2a_agent(self, base_url):
        """Update an A2A agent."""
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
    
    def _delete_a2a_agent(self, base_url):
        """Delete an A2A agent."""
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