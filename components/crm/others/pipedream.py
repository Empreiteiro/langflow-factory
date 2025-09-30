from langflow.custom import Component
from langflow.io import (
    StrInput,
    SecretStrInput,
    DropdownInput,
    IntInput,
    Output,
    DataInput,
    MessageInput,
    HandleInput,
)
from langflow.inputs import SortableListInput
from langflow.schema import Data
import requests
import json
from typing import Any


class PipedreamConnectComponent(Component):
    """
    Componente Langflow para interagir com a Pipedream Connect API.

    Funcionalidades implementadas baseadas na documentação oficial:
    - Gerenciamento de tokens (OAuth e Connect tokens)
    - Operações com Apps (listar, recuperar, categorias)
    - Gerenciamento de Accounts (listar, recuperar, deletar)
    - Operações com Components (listar, recuperar)
    - Actions (listar, recuperar, configurar, executar)
    - Triggers (listar, recuperar, configurar, deploy)
    - Deployed Triggers (listar, atualizar, deletar)
    """

    display_name = "Pipedream Connect"
    description = "Complete integration with Pipedream Connect API - manage tokens, apps, accounts, components, actions, and triggers."
    icon = "cloud"
    name = "PipedreamConnect"
    beta = False

    inputs = [
        HandleInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the Pipedream Connect action. Connect any component output here to trigger the action.",
            input_types=["Text", "Data", "DataFrame"],
            required=False,
        ),
        StrInput(
            name="project_id",
            display_name="Project ID",
            info="Your Pipedream project ID (required for Connect API calls).",
            required=True,
        ),
        StrInput(
            name="environment",
            display_name="Environment",
            info="Environment for the project (development or production).",
            value="development",
            required=True,
        ),
        SecretStrInput(
            name="client_id",
            display_name="OAuth Client ID",
            info="OAuth Client ID for authentication.",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="client_secret",
            display_name="OAuth Client Secret",
            info="OAuth Client Secret for authentication.",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="access_token",
            display_name="Access Token",
            info="Pre-generated access token (if available).",
            required=False,
            advanced=True,
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="Pipedream Connect API action to perform.",
            options=[
                {"name": "Generate OAuth Token", "icon": "key"},
                {"name": "Create Connect Token", "icon": "plus"},
                {"name": "List Apps", "icon": "list"},
                {"name": "Retrieve App", "icon": "info"},
                {"name": "List App Categories", "icon": "folder"},
                {"name": "List Accounts", "icon": "users"},
                {"name": "Retrieve Account", "icon": "user"},
                {"name": "Delete Account", "icon": "trash"},
                {"name": "Delete Accounts by App", "icon": "trash-2"},
                {"name": "List Components", "icon": "grid"},
                {"name": "Retrieve Component", "icon": "box"},
                {"name": "List Actions", "icon": "play"},
                {"name": "Retrieve Action", "icon": "play-circle"},
                {"name": "Run Action", "icon": "zap"},
                {"name": "List Triggers", "icon": "radio"},
                {"name": "Retrieve Trigger", "icon": "target"},
                {"name": "Deploy Trigger", "icon": "upload"},
                {"name": "List Deployed Triggers", "icon": "server"},
                {"name": "Get Deployed Trigger", "icon": "eye"},
                {"name": "Update Deployed Trigger", "icon": "edit"},
                {"name": "Delete Deployed Trigger", "icon": "x"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Dynamic inputs (initially hidden)
        MessageInput(
            name="external_user_id",
            display_name="External User ID",
            info="Your user's ID in your system (max 250 characters).",
            show=False,
            tool_mode=True,
        ),
        StrInput(
            name="app_id",
            display_name="App ID",
            info="ID of the app to retrieve or work with.",
            show=False,
        ),
        StrInput(
            name="account_id",
            display_name="Account ID",
            info="ID of the account to retrieve or delete.",
            show=False,
        ),
        StrInput(
            name="component_id",
            display_name="Component ID",
            info="ID of the component to retrieve.",
            show=False,
        ),
        StrInput(
            name="action_id",
            display_name="Action ID",
            info="ID of the action to retrieve or run.",
            show=False,
        ),
        StrInput(
            name="trigger_id",
            display_name="Trigger ID",
            info="ID of the trigger to retrieve or deploy.",
            show=False,
        ),
        StrInput(
            name="deployed_trigger_id",
            display_name="Deployed Trigger ID",
            info="ID of the deployed trigger to manage.",
            show=False,
        ),
        DataInput(
            name="action_props",
            display_name="Action Props",
            info="Props/configuration for the action (JSON format).",
            show=False,
            tool_mode=True,
        ),
        DataInput(
            name="trigger_props",
            display_name="Trigger Props",
            info="Props/configuration for the trigger (JSON format).",
            show=False,
            tool_mode=True,
        ),
        DataInput(
            name="update_data",
            display_name="Update Data",
            info="Data to update for deployed triggers (JSON format).",
            show=False,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="execute_action"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Generate OAuth Token": [],
            "Create Connect Token": ["external_user_id"],
            "List Apps": [],
            "Retrieve App": ["app_id"],
            "List App Categories": [],
            "List Accounts": ["external_user_id"],
            "Retrieve Account": ["account_id"],
            "Delete Account": ["account_id"],
            "Delete Accounts by App": ["app_id", "external_user_id"],
            "List Components": ["app_id"],
            "Retrieve Component": ["component_id"],
            "List Actions": ["app_id"],
            "Retrieve Action": ["action_id"],
            "Run Action": ["action_id", "action_props"],
            "List Triggers": ["app_id"],
            "Retrieve Trigger": ["trigger_id"],
            "Deploy Trigger": ["trigger_id", "trigger_props"],
            "List Deployed Triggers": ["external_user_id"],
            "Get Deployed Trigger": ["deployed_trigger_id"],
            "Update Deployed Trigger": ["deployed_trigger_id", "update_data"],
            "Delete Deployed Trigger": ["deployed_trigger_id"],
        }

        # Hide all dynamic fields first
        for field_name in ["external_user_id", "app_id", "account_id", "component_id", "action_id", 
                          "trigger_id", "deployed_trigger_id", "action_props", "trigger_props", "update_data"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def _get_base_url(self) -> str:
        """Get the base URL for Pipedream Connect API with project ID."""
        return f"https://api.pipedream.com/v1/connect/{self.project_id}"

    def _get_headers(self, token: str = None) -> dict:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "X-PD-Environment": self.environment or "development"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _make_request(self, method: str, endpoint: str, data: dict = None, token: str = None) -> dict:
        """Make HTTP request to Pipedream Connect API."""
        url = f"{self._get_base_url()}/{endpoint.lstrip('/')}"
        headers = self._get_headers(token)
        
        try:
            self.log(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            
            try:
                return {"success": True, "status_code": response.status_code, "data": response.json()}
            except ValueError:
                return {"success": True, "status_code": response.status_code, "text": response.text}
                
        except requests.RequestException as e:
            self.log(f"API request error: {str(e)}")
            return {"error": str(e)}

    def _get_access_token(self) -> str:
        """Get access token, generate if needed."""
        # Use provided access token if available
        if self.access_token:
            return self.access_token
            
        # Generate OAuth token if client credentials are provided
        if self.client_id and self.client_secret:
            token_result = self._generate_oauth_token()
            if token_result.get("success"):
                return token_result.get("data", {}).get("access_token")
        
        return None

    def _generate_oauth_token(self) -> dict:
        """Generate OAuth token using client credentials."""
        if not self.client_id or not self.client_secret:
            return {"error": "Client ID and Client Secret are required for token generation"}

        url = "https://api.pipedream.com/v1/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=30)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            self.log(f"Error generating OAuth token: {str(e)}")
            return {"error": str(e)}

    def _extract_message_text(self, message_input):
        """Extract text from MessageInput object."""
        if hasattr(message_input, 'text'):
            return message_input.text
        elif hasattr(message_input, 'content'):
            return message_input.content
        elif hasattr(message_input, 'message'):
            return message_input.message
        else:
            return str(message_input) if message_input else None

    def execute_action(self) -> Data:
        """Execute the selected Pipedream Connect API action."""
        try:
            # Validate required inputs
            if not hasattr(self, 'project_id') or not self.project_id:
                return Data(data={"error": "Project ID is required"})
            
            if not hasattr(self, 'action') or not self.action:
                return Data(data={"error": "Action is required"})

            # Extract action name from the selected action
            action_name = None
            if isinstance(self.action, list) and len(self.action) > 0:
                action_name = self.action[0].get("name")
            elif isinstance(self.action, dict):
                action_name = self.action.get("name")
            
            if not action_name:
                return Data(data={"error": "Invalid action selected"})

            # Get access token for authenticated requests
            access_token = self._get_access_token()

            # Execute the appropriate action
            if action_name == "Generate OAuth Token":
                result = self._generate_oauth_token()
                if result.get("success"):
                    self.status = "OAuth token generated successfully"
                else:
                    self.status = f"Error generating token: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Create Connect Token":
                external_user_id = self._extract_message_text(getattr(self, 'external_user_id', None))
                if not external_user_id:
                    return Data(data={"error": "External User ID is required for creating Connect token"})
                
                data = {"external_user_id": external_user_id}
                result = self._make_request("POST", "tokens", data, access_token)
                if result.get("success"):
                    self.status = "Connect token created successfully"
                else:
                    self.status = f"Error creating Connect token: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Apps":
                result = self._make_request("GET", "apps", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved {len(result.get('data', {}).get('data', []))} apps"
                else:
                    self.status = f"Error listing apps: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Retrieve App":
                app_id = getattr(self, 'app_id', None)
                if not app_id:
                    return Data(data={"error": "App ID is required"})
                
                result = self._make_request("GET", f"apps/{app_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved app {app_id}"
                else:
                    self.status = f"Error retrieving app: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List App Categories":
                result = self._make_request("GET", "apps/categories", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved {len(result.get('data', {}).get('data', []))} app categories"
                else:
                    self.status = f"Error listing app categories: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Accounts":
                external_user_id = self._extract_message_text(getattr(self, 'external_user_id', None))
                if not external_user_id:
                    return Data(data={"error": "External User ID is required"})
                
                result = self._make_request("GET", f"accounts?external_user_id={external_user_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved accounts for user {external_user_id}"
                else:
                    self.status = f"Error listing accounts: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Retrieve Account":
                account_id = getattr(self, 'account_id', None)
                if not account_id:
                    return Data(data={"error": "Account ID is required"})
                
                result = self._make_request("GET", f"accounts/{account_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved account {account_id}"
                else:
                    self.status = f"Error retrieving account: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Delete Account":
                account_id = getattr(self, 'account_id', None)
                if not account_id:
                    return Data(data={"error": "Account ID is required"})
                
                result = self._make_request("DELETE", f"accounts/{account_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Deleted account {account_id}"
                else:
                    self.status = f"Error deleting account: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Delete Accounts by App":
                app_id = getattr(self, 'app_id', None)
                external_user_id = self._extract_message_text(getattr(self, 'external_user_id', None))
                if not app_id or not external_user_id:
                    return Data(data={"error": "App ID and External User ID are required"})
                
                result = self._make_request("DELETE", f"accounts/app/{app_id}?external_user_id={external_user_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Deleted accounts for app {app_id} and user {external_user_id}"
                else:
                    self.status = f"Error deleting accounts: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Components":
                app_id = getattr(self, 'app_id', None)
                if not app_id:
                    return Data(data={"error": "App ID is required"})
                
                result = self._make_request("GET", f"components?app_id={app_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved components for app {app_id}"
                else:
                    self.status = f"Error listing components: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Retrieve Component":
                component_id = getattr(self, 'component_id', None)
                if not component_id:
                    return Data(data={"error": "Component ID is required"})
                
                result = self._make_request("GET", f"components/{component_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved component {component_id}"
                else:
                    self.status = f"Error retrieving component: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Actions":
                app_id = getattr(self, 'app_id', None)
                if not app_id:
                    return Data(data={"error": "App ID is required"})
                
                result = self._make_request("GET", f"actions?app_id={app_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved actions for app {app_id}"
                else:
                    self.status = f"Error listing actions: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Retrieve Action":
                action_id = getattr(self, 'action_id', None)
                if not action_id:
                    return Data(data={"error": "Action ID is required"})
                
                result = self._make_request("GET", f"actions/{action_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved action {action_id}"
                else:
                    self.status = f"Error retrieving action: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Run Action":
                action_id = getattr(self, 'action_id', None)
                action_props = getattr(self, 'action_props', None)
                if not action_id:
                    return Data(data={"error": "Action ID is required"})
                
                # Process action props
                props_data = {}
                if action_props:
                    if hasattr(action_props, 'data'):
                        props_data = action_props.data
                    elif isinstance(action_props, str):
                        props_data = json.loads(action_props)
                    else:
                        props_data = action_props
                
                result = self._make_request("POST", f"actions/{action_id}/run", props_data, access_token)
                if result.get("success"):
                    self.status = f"Executed action {action_id}"
                else:
                    self.status = f"Error running action: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Triggers":
                app_id = getattr(self, 'app_id', None)
                if not app_id:
                    return Data(data={"error": "App ID is required"})
                
                result = self._make_request("GET", f"triggers?app_id={app_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved triggers for app {app_id}"
                else:
                    self.status = f"Error listing triggers: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Retrieve Trigger":
                trigger_id = getattr(self, 'trigger_id', None)
                if not trigger_id:
                    return Data(data={"error": "Trigger ID is required"})
                
                result = self._make_request("GET", f"triggers/{trigger_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved trigger {trigger_id}"
                else:
                    self.status = f"Error retrieving trigger: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Deploy Trigger":
                trigger_id = getattr(self, 'trigger_id', None)
                trigger_props = getattr(self, 'trigger_props', None)
                if not trigger_id:
                    return Data(data={"error": "Trigger ID is required"})
                
                # Process trigger props
                props_data = {}
                if trigger_props:
                    if hasattr(trigger_props, 'data'):
                        props_data = trigger_props.data
                    elif isinstance(trigger_props, str):
                        props_data = json.loads(trigger_props)
                    else:
                        props_data = trigger_props
                
                result = self._make_request("POST", f"triggers/{trigger_id}/deploy", props_data, access_token)
                if result.get("success"):
                    self.status = f"Deployed trigger {trigger_id}"
                else:
                    self.status = f"Error deploying trigger: {result.get('error')}"
                return Data(data=result)

            elif action_name == "List Deployed Triggers":
                external_user_id = self._extract_message_text(getattr(self, 'external_user_id', None))
                if not external_user_id:
                    return Data(data={"error": "External User ID is required"})
                
                result = self._make_request("GET", f"deployed_triggers?external_user_id={external_user_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved deployed triggers for user {external_user_id}"
                else:
                    self.status = f"Error listing deployed triggers: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Get Deployed Trigger":
                deployed_trigger_id = getattr(self, 'deployed_trigger_id', None)
                if not deployed_trigger_id:
                    return Data(data={"error": "Deployed Trigger ID is required"})
                
                result = self._make_request("GET", f"deployed_triggers/{deployed_trigger_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Retrieved deployed trigger {deployed_trigger_id}"
                else:
                    self.status = f"Error retrieving deployed trigger: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Update Deployed Trigger":
                deployed_trigger_id = getattr(self, 'deployed_trigger_id', None)
                update_data = getattr(self, 'update_data', None)
                if not deployed_trigger_id:
                    return Data(data={"error": "Deployed Trigger ID is required"})
                
                # Process update data
                data_to_update = {}
                if update_data:
                    if hasattr(update_data, 'data'):
                        data_to_update = update_data.data
                    elif isinstance(update_data, str):
                        data_to_update = json.loads(update_data)
                    else:
                        data_to_update = update_data
                
                result = self._make_request("PUT", f"deployed_triggers/{deployed_trigger_id}", data_to_update, access_token)
                if result.get("success"):
                    self.status = f"Updated deployed trigger {deployed_trigger_id}"
                else:
                    self.status = f"Error updating deployed trigger: {result.get('error')}"
                return Data(data=result)

            elif action_name == "Delete Deployed Trigger":
                deployed_trigger_id = getattr(self, 'deployed_trigger_id', None)
                if not deployed_trigger_id:
                    return Data(data={"error": "Deployed Trigger ID is required"})
                
                result = self._make_request("DELETE", f"deployed_triggers/{deployed_trigger_id}", token=access_token)
                if result.get("success"):
                    self.status = f"Deleted deployed trigger {deployed_trigger_id}"
                else:
                    self.status = f"Error deleting deployed trigger: {result.get('error')}"
                return Data(data=result)

            else:
                return Data(data={"error": f"Unsupported action: {action_name}"})

        except Exception as e:
            error_msg = f"Unexpected error executing {action_name}: {str(e)}"
            self.log(error_msg)
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})
