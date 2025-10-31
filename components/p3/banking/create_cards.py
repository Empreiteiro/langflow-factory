"""
P3 Card Creation Component

This component creates a card in the P3 Banking API by making a POST request
to the /v2/realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId/cards endpoint.
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data


class P3CreateCardComponent(Component):
    display_name = "P3 Create Card"
    description = "Create a card in the P3 Banking API"
    icon = "credit-card"
    name = "P3CreateCardComponent"
    
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
            name="card_name",
            display_name="Name",
            info="Name of the card",
            required=True,
        ),
        StrInput(
            name="type",
            display_name="Type",
            info="Type of the card (e.g., VIRTUAL)",
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
        Output(name="response", display_name="Response", method="create_card"),
    ]
    
    def create_card(self) -> Data:
        """
        Create a card in the P3 Banking API.
        
        Returns:
            Data: Contains the response from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/v2/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}/cards"
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
        
        # Prepare request body
        body = {
            "name": self.card_name,
            "type": self.type,
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
