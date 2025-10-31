"""
P3 Get Wallet Component

This component retrieves wallet information from the P3 Banking API by making a GET request
to the /v2/realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId endpoint.
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data


class P3GetWalletComponent(Component):
    display_name = "P3 Get Wallet"
    description = "Get wallet information from the P3 Banking API"
    icon = "wallet"
    name = "P3GetWalletComponent"
    
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
        Output(name="response", display_name="Response", method="get_wallet"),
    ]
    
    def get_wallet(self) -> Data:
        """
        Get wallet information from the P3 Banking API.
        
        Returns:
            Data: Contains the wallet information from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/v2/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}"
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
        if hasattr(self, 'banking_environment') and self.banking_environment:
            headers["x-environment"] = self.banking_environment
        
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
