"""
P3 List Wallet Cards Platform Component

This component lists cards from a wallet in the P3 Platform API by making a GET request
to the /realms/:realmId/organizations/:organizationId/wallets/:walletId/cards endpoint.
"""

import json
import requests
from urllib.parse import urlencode

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data


class P3ListWalletCardsPlatformComponent(Component):
    display_name = "P3 List Wallet Cards Platform"
    description = "List cards from a wallet in the P3 Platform API"
    icon = "credit-card"
    name = "P3ListWalletCardsPlatformComponent"
    
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
        StrInput(
            name="wallet_id",
            display_name="Wallet ID",
            info="The wallet ID to list cards from",
            required=True,
        ),
        SecretStrInput(
            name="access_token",
            display_name="Access Token",
            info="Bearer token for authentication",
            required=True,
        ),
        StrInput(
            name="card_status",
            display_name="Status",
            info="Optional status filter for cards (e.g., BLOCKED)",
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
        Output(name="response", display_name="Response", method="list_wallet_cards"),
    ]
    
    def list_wallet_cards(self) -> Data:
        """
        List cards from a wallet in the P3 Platform API.
        
        Returns:
            Data: Contains the list of cards from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.platform.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"wallets/{self.wallet_id}/cards"
        )
        
        # Add query parameters if provided
        query_params = {}
        card_status = getattr(self, 'card_status', None)
        if card_status:
            query_params['status'] = card_status
        
        if query_params:
            url += '?' + urlencode(query_params)
        
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
        
        try:
            # Make GET request
            response = requests.get(
                url,
                headers=headers,
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
