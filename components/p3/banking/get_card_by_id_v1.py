"""
P3 Get Card V1 Component

This component retrieves card information from the P3 Banking API by making a GET request
to the /realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId/cards/:cardId endpoint (V1 version).
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data


class P3GetCardV1Component(Component):
    display_name = "P3 Get Card V1"
    description = "Get card information by ID from the P3 Banking API (V1 version)"
    icon = "credit-card"
    name = "P3GetCardV1Component"
    
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
            name="account_id",
            display_name="Account ID",
            info="The account ID for the request",
            required=True,
        ),
        StrInput(
            name="wallet_id",
            display_name="Wallet ID",
            info="The wallet ID for the request",
            required=True,
        ),
        StrInput(
            name="card_id",
            display_name="Card ID",
            info="The card ID to retrieve",
            required=True,
        ),
        SecretStrInput(
            name="access_token",
            display_name="Access Token",
            info="Bearer token for authentication",
            required=True,
        ),
        StrInput(
            name="banking_environment",
            display_name="Banking Environment",
            info="Banking environment value for x-environment header",
            required=False,
        ),
    ]
    
    outputs = [
        Output(name="response", display_name="Response", method="get_card_v1"),
    ]
    
    def get_card_v1(self) -> Data:
        """
        Get card information by ID from the P3 Banking API (V1 version).
        
        Returns:
            Data: Contains the card information from the API
        """
        # Build the URL with path parameters (V1 version - without /v2 prefix)
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}/cards/{self.card_id}"
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
        banking_env = getattr(self, 'banking_environment', None)
        if banking_env:
            headers["x-environment"] = banking_env
        
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
