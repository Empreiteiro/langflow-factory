"""
P3 Create Wallet Platform Component

This component creates a wallet in the P3 Platform API by making a POST request
to the /realms/:realmId/organizations/:organizationId/wallets endpoint.
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, DropdownInput, BoolInput, Output
from langflow.inputs.inputs import DictInput
from langflow.schema import Data


class P3CreateWalletPlatformComponent(Component):
    display_name = "P3 Create Wallet Platform"
    description = "Create a wallet in the P3 Platform API"
    icon = "wallet"
    name = "P3CreateWalletPlatformComponent"
    
    inputs = [
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
            name="wallet_name",
            display_name="Name",
            info="Name of the wallet",
            required=True,
        ),
        DropdownInput(
            name="wallet_type",
            display_name="Type",
            info="Type of the wallet: PERSONAL or SHARED",
            options=["PERSONAL", "SHARED"],
            value="PERSONAL",
            required=True,
        ),
        DictInput(
            name="shared_users",
            display_name="Shared Users",
            info="Array of shared users (required if type is SHARED). Each item should have 'id' and 'role' fields.",
            list=True,
            required=False,
        ),
        BoolInput(
            name="pix_enabled",
            display_name="PIX Enabled",
            info="Enable PIX payment method",
            value=False,
            required=False,
        ),
        BoolInput(
            name="bank_slip_enabled",
            display_name="Bank Slip Enabled",
            info="Enable bank slip payment method",
            value=False,
            required=False,
        ),
        BoolInput(
            name="card_enabled",
            display_name="Card Enabled",
            info="Enable card payment method",
            value=False,
            required=False,
        ),
        StrInput(
            name="platform_environment",
            display_name="Platform Environment",
            info="Platform environment value for x-environment header",
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="response", display_name="Response", method="create_wallet"),
    ]
    
    def create_wallet(self) -> Data:
        """
        Create a wallet in the P3 Platform API.
        
        Returns:
            Data: Contains the response from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/wallets"
        )
        
        # Get access token
        access_token = self.access_token
        if hasattr(self.access_token, 'get_secret_value'):
            access_token = self.access_token.get_secret_value()
        elif isinstance(self.access_token, str):
            access_token = self.access_token
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # Add x-environment header if provided
        platform_env = getattr(self, 'platform_environment', None)
        if platform_env:
            headers["x-environment"] = platform_env
        
        # Prepare request body
        body = {
            "name": self.wallet_name,
            "type": self.wallet_type,
        }
        
        # Add shared users if type is SHARED
        if self.wallet_type == "SHARED":
            shared_users_data = getattr(self, 'shared_users', None)
            
            # Handle different input formats
            if shared_users_data is None:
                shared_users_data = []
            elif isinstance(shared_users_data, str):
                try:
                    shared_users_data = json.loads(shared_users_data)
                except json.JSONDecodeError:
                    return Data(
                        value={
                            "status": "error",
                            "message": "Invalid JSON in shared_users",
                            "error": "shared_users must be valid JSON",
                        }
                    )
            elif hasattr(shared_users_data, 'data'):
                shared_users_data = shared_users_data.data
            elif hasattr(shared_users_data, 'value'):
                shared_users_data = shared_users_data.value
            
            # Ensure it's a list (each item should be a dict with id and role)
            if isinstance(shared_users_data, dict):
                shared_users_data = [shared_users_data]
            elif not isinstance(shared_users_data, list):
                return Data(
                    value={
                        "status": "error",
                        "message": "shared_users must be an array",
                        "error": "shared_users must be a list of objects, where each object has 'id' and 'role' fields",
                    }
                )
            
            # Validate that we have at least one item
            if not shared_users_data or len(shared_users_data) == 0:
                return Data(
                    value={
                        "status": "error",
                        "message": "shared_users is required when type is SHARED",
                        "error": "For SHARED wallets, you must provide at least one shared user",
                    }
                )
            
            # Validate each item is a dict with id and role fields
            has_owner = False
            validated_shared = []
            
            for idx, item in enumerate(shared_users_data):
                # Each item must be a dictionary
                if not isinstance(item, dict):
                    return Data(
                        value={
                            "status": "error",
                            "message": f"shared_users[{idx}] must be an object",
                            "error": f"Each item in shared_users must be an object with 'id' and 'role' fields. Received type: {type(item).__name__}",
                        }
                    )
                
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
                    return Data(
                        value={
                            "status": "error",
                            "message": f"shared_users[{idx}].id is required",
                            "error": f"Each shared user must have an 'id' field. Available keys: {list(item.keys())}",
                        }
                    )
                
                # Validate role field
                if item_role is None or (isinstance(item_role, str) and not item_role.strip()):
                    return Data(
                        value={
                            "status": "error",
                            "message": f"shared_users[{idx}].role is required",
                            "error": f"Each shared user must have a 'role' field (OWNER or USER). Available keys: {list(item.keys())}",
                        }
                    )
                
                # Normalize role to uppercase
                role_upper = str(item_role).strip().upper()
                if role_upper not in ["OWNER", "USER"]:
                    return Data(
                        value={
                            "status": "error",
                            "message": f"shared_users[{idx}].role must be OWNER or USER",
                            "error": f"Role must be either 'OWNER' or 'USER', received: {item_role}",
                        }
                    )
                
                if role_upper == "OWNER":
                    has_owner = True
                
                # Add validated shared user (only id and role fields)
                validated_shared.append({
                    "id": str(item_id).strip(),
                    "role": role_upper
                })
            
            # Validate that at least one user has OWNER role
            if not has_owner:
                return Data(
                    value={
                        "status": "error",
                        "message": "shared must have at least one item with role OWNER",
                        "error": "At least one shared user must have role 'OWNER'",
                    }
                )
            
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
        
        try:
            # Make POST request
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=30
            )
            
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
            return Data(
                value={
                    "status": "error",
                    "message": "Request timed out after 30 seconds",
                    "url": url,
                }
            )
        except requests.exceptions.ConnectionError:
            return Data(
                value={
                    "status": "error",
                    "message": "Connection failed. Check if the API server is reachable.",
                    "url": url,
                }
            )
        except requests.exceptions.RequestException as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Request failed: {str(e)}",
                    "url": url,
                }
            )
        except Exception as e:
            return Data(
                value={
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "url": url,
                }
            )
