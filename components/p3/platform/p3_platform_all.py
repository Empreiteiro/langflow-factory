"""
P3 Platform All-in-One Component

This component consolidates all P3 Platform API actions into a single unified interface.
Each action appears as a separate output/tool. Connect to the desired output to execute that specific action.
"""

import json
import requests
from urllib.parse import urlencode

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, DropdownInput, BoolInput, IntInput, Output, DataInput
from langflow.inputs.inputs import DictInput
from langflow.schema import Data


class P3PlatformAllComponent(Component):
    display_name = "P3 Platform"
    description = "Unified component for all P3 Platform API operations. Each action appears as a separate output. Connect to the desired output to execute that specific action."
    icon = "server"
    name = "P3PlatformAllComponent"
    
    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the P3 Platform action. Connect any component output here to trigger the action.",
            required=False,
        ),
        # Common inputs
        StrInput(
            name="realm_id",
            display_name="Realm ID",
            info="The realm ID for the request",
            required=True,
        ),
        StrInput(
            name="organization_id",
            display_name="Organization ID",
            info="The organization ID for the request",
            required=True,
        ),
        SecretStrInput(
            name="access_token",
            display_name="Access Token",
            info="Bearer token for authentication",
            required=True,
        ),
        StrInput(
            name="platform_environment",
            display_name="Platform Environment",
            info="Platform environment value for x-environment header",
            required=False,
            advanced=True,
        ),
        # Wallet-specific inputs (initially hidden)
        StrInput(
            name="wallet_id",
            display_name="Wallet ID",
            show=False,
            info="The wallet ID for the request",
            tool_mode=True,
        ),
        StrInput(
            name="wallet_name",
            display_name="Wallet Name",
            show=False,
            info="Name of the wallet",
            tool_mode=True,
        ),
        DropdownInput(
            name="wallet_type",
            display_name="Wallet Type",
            show=False,
            info="Type of the wallet: PERSONAL or SHARED",
            options=["PERSONAL", "SHARED"],
            value="PERSONAL",
            tool_mode=True,
        ),
        DictInput(
            name="shared_users",
            display_name="Shared Users",
            show=False,
            info="Array of shared users (required if type is SHARED). Each item should have 'id' and 'role' fields.",
            list=True,
            tool_mode=True,
        ),
        BoolInput(
            name="pix_enabled",
            display_name="PIX Enabled",
            show=False,
            info="Enable PIX payment method",
            value=False,
            tool_mode=True,
        ),
        BoolInput(
            name="bank_slip_enabled",
            display_name="Bank Slip Enabled",
            show=False,
            info="Enable bank slip payment method",
            value=False,
            tool_mode=True,
        ),
        BoolInput(
            name="card_enabled",
            display_name="Card Enabled",
            show=False,
            info="Enable card payment method",
            value=False,
            tool_mode=True,
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            show=False,
            info="Maximum number of wallets to return",
            tool_mode=True,
        ),
        # Card-specific inputs (initially hidden)
        StrInput(
            name="card_name",
            display_name="Card Name",
            show=False,
            info="Name of the card",
            tool_mode=True,
        ),
        StrInput(
            name="card_type",
            display_name="Card Type",
            show=False,
            info="Type of the card (e.g., VIRTUAL)",
            tool_mode=True,
        ),
        StrInput(
            name="card_status",
            display_name="Card Status",
            show=False,
            info="Optional status filter for cards (e.g., BLOCKED)",
            tool_mode=True,
        ),
    ]
    
    outputs = [
        # Wallet Management
        Output(name="create_wallet", display_name="Create Wallet", method="create_wallet"),
        Output(name="list_wallets", display_name="List Wallets", method="list_wallets"),
        Output(name="get_wallet_by_id", display_name="Get Wallet By ID", method="get_wallet_by_id"),
        # Card Management
        Output(name="create_card", display_name="Create Card", method="create_card"),
        Output(name="list_wallet_cards", display_name="List Wallet Cards", method="list_wallet_cards"),
        Output(name="list_organization_cards", display_name="List Organization Cards", method="list_organization_cards"),
    ]
    
    def _get_access_token(self):
        """Helper to extract access token value from SecretStrInput."""
        token_value = self.access_token
        if hasattr(self.access_token, 'get_secret_value'):
            token_value = self.access_token.get_secret_value()
        elif isinstance(self.access_token, str):
            token_value = self.access_token
        return token_value
    
    def _get_headers(self):
        """Helper to build common headers."""
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }
        platform_env = getattr(self, 'platform_environment', None)
        if platform_env:
            headers["x-environment"] = platform_env
        return headers
    
    def _make_request(self, method, url, headers=None, json_data=None, params=None, timeout=30):
        """Helper to make HTTP requests with consistent error handling."""
        if headers is None:
            headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=json_data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return Data(value={
                    "status": "error",
                    "message": f"Unsupported HTTP method: {method}",
                    "url": url,
                })
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                result = {
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "data": response_data,
                    "url": url,
                }
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, return raw response
                result = {
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "raw_response": response.text,
                    "url": url,
                }
            
            # Log error if status code indicates failure
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                self.log(error_msg)
                result["message"] = error_msg
            
            return Data(value=result)
            
        except requests.exceptions.Timeout:
            return Data(value={
                "status": "error",
                "message": f"Request timed out after {timeout} seconds",
                "url": url,
            })
        except requests.exceptions.ConnectionError:
            return Data(value={
                "status": "error",
                "message": "Connection failed. Check if the API server is reachable.",
                "url": url,
            })
        except requests.exceptions.RequestException as e:
            return Data(value={
                "status": "error",
                "message": f"Request failed: {str(e)}",
                "url": url,
            })
        except Exception as e:
            return Data(value={
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "url": url,
            })
    
    # Wallet Management Methods
    def create_wallet(self) -> Data:
        """Create a wallet in the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/wallets"
        
        wallet_name = getattr(self, 'wallet_name', None)
        wallet_type = getattr(self, 'wallet_type', 'PERSONAL')
        
        if not wallet_name:
            return Data(value={"status": "error", "message": "Wallet name is required"})
        
        body = {
            "name": wallet_name,
            "type": wallet_type,
        }
        
        # Add shared users if type is SHARED
        if wallet_type == "SHARED":
            shared_users_data = getattr(self, 'shared_users', None)
            
            # Handle different input formats
            if shared_users_data is None:
                shared_users_data = []
            elif isinstance(shared_users_data, str):
                try:
                    shared_users_data = json.loads(shared_users_data)
                except json.JSONDecodeError:
                    return Data(value={
                        "status": "error",
                        "message": "Invalid JSON in shared_users",
                        "error": "shared_users must be valid JSON",
                    })
            elif hasattr(shared_users_data, 'data'):
                shared_users_data = shared_users_data.data
            elif hasattr(shared_users_data, 'value'):
                shared_users_data = shared_users_data.value
            
            # Ensure it's a list
            if isinstance(shared_users_data, dict):
                shared_users_data = [shared_users_data]
            elif not isinstance(shared_users_data, list):
                return Data(value={
                    "status": "error",
                    "message": "shared_users must be an array",
                    "error": "shared_users must be a list of objects, where each object has 'id' and 'role' fields",
                })
            
            # Validate that we have at least one item
            if not shared_users_data or len(shared_users_data) == 0:
                return Data(value={
                    "status": "error",
                    "message": "shared_users is required when type is SHARED",
                    "error": "For SHARED wallets, you must provide at least one shared user",
                })
            
            # Validate each item is a dict with id and role fields
            has_owner = False
            validated_shared = []
            
            for idx, item in enumerate(shared_users_data):
                if not isinstance(item, dict):
                    return Data(value={
                        "status": "error",
                        "message": f"shared_users[{idx}] must be an object",
                        "error": f"Each item in shared_users must be an object with 'id' and 'role' fields. Received type: {type(item).__name__}",
                    })
                
                # Extract id and role (case-insensitive key matching)
                item_id = None
                item_role = None
                
                for key, value in item.items():
                    key_lower = str(key).lower().strip()
                    if key_lower == 'id':
                        item_id = value
                    elif key_lower == 'role':
                        item_role = value
                
                # Validate id field
                if item_id is None or (isinstance(item_id, str) and not item_id.strip()):
                    return Data(value={
                        "status": "error",
                        "message": f"shared_users[{idx}].id is required",
                        "error": f"Each shared user must have an 'id' field. Available keys: {list(item.keys())}",
                    })
                
                # Validate role field
                if item_role is None or (isinstance(item_role, str) and not item_role.strip()):
                    return Data(value={
                        "status": "error",
                        "message": f"shared_users[{idx}].role is required",
                        "error": f"Each shared user must have a 'role' field (OWNER or USER). Available keys: {list(item.keys())}",
                    })
                
                # Normalize role to uppercase
                role_upper = str(item_role).strip().upper()
                if role_upper not in ["OWNER", "USER"]:
                    return Data(value={
                        "status": "error",
                        "message": f"shared_users[{idx}].role must be OWNER or USER",
                        "error": f"Role must be either 'OWNER' or 'USER', received: {item_role}",
                    })
                
                if role_upper == "OWNER":
                    has_owner = True
                
                validated_shared.append({
                    "id": str(item_id).strip(),
                    "role": role_upper
                })
            
            # Validate that at least one user has OWNER role
            if not has_owner:
                return Data(value={
                    "status": "error",
                    "message": "shared must have at least one item with role OWNER",
                    "error": "At least one shared user must have role 'OWNER'",
                })
            
            body["shared"] = validated_shared
        
        # Build settings object with payment configurations
        pix_enabled = getattr(self, 'pix_enabled', False)
        bank_slip_enabled = getattr(self, 'bank_slip_enabled', False)
        card_enabled = getattr(self, 'card_enabled', False)
        
        body["settings"] = {
            "payment": {
                "pix": bool(pix_enabled),
                "bankSlip": bool(bank_slip_enabled),
                "card": bool(card_enabled),
            }
        }
        
        return self._make_request("POST", url, json_data=body)
    
    def list_wallets(self) -> Data:
        """List wallets from an organization in the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/wallets"
        
        params = {}
        limit_value = getattr(self, 'limit', None)
        if limit_value:
            params['limit'] = limit_value
        
        return self._make_request("GET", url, params=params)
    
    def get_wallet_by_id(self) -> Data:
        """Get wallet information by ID from the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        wallet_id = getattr(self, 'wallet_id', None)
        if not wallet_id:
            return Data(value={"status": "error", "message": "Wallet ID is required"})
        
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/wallets/{wallet_id}"
        return self._make_request("GET", url)
    
    # Card Management Methods
    def create_card(self) -> Data:
        """Create a card in the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        wallet_id = getattr(self, 'wallet_id', None)
        card_name = getattr(self, 'card_name', None)
        card_type = getattr(self, 'card_type', None)
        
        if not wallet_id:
            return Data(value={"status": "error", "message": "Wallet ID is required"})
        if not card_name:
            return Data(value={"status": "error", "message": "Card name is required"})
        if not card_type:
            return Data(value={"status": "error", "message": "Card type is required"})
        
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/wallets/{wallet_id}/cards"
        
        body = {
            "name": card_name,
            "type": card_type,
        }
        
        return self._make_request("POST", url, json_data=body)
    
    def list_wallet_cards(self) -> Data:
        """List cards from a wallet in the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        wallet_id = getattr(self, 'wallet_id', None)
        if not wallet_id:
            return Data(value={"status": "error", "message": "Wallet ID is required"})
        
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/wallets/{wallet_id}/cards"
        
        params = {}
        card_status = getattr(self, 'card_status', None)
        if card_status:
            params['status'] = card_status
        
        return self._make_request("GET", url, params=params)
    
    def list_organization_cards(self) -> Data:
        """List cards from an organization in the P3 Platform API."""
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        url = f"{base_url}/realms/{self.realm_id}/organizations/{self.organization_id}/cards"
        return self._make_request("GET", url)

