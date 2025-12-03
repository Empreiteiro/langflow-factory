"""
P3 PIX Dict (PIX Key) Component

This component creates a PIX key in the P3 Banking API by making a POST request
to the /realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId/pix-dict endpoint.
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, DropdownInput
from langflow.schema import Data


class P3PixDictComponent(Component):
    display_name = "P3 PIX Dict"
    description = "Create a PIX key in the P3 Banking API"
    icon = "key"
    name = "P3PixDictComponent"
    
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
        DropdownInput(
            name="pix_key_type",
            display_name="PIX Key Type",
            options=["EMAIL", "CPF", "CNPJ", "PHONE", "RANDOM"],
            value="EMAIL",
            info="Type of PIX key to create",
            required=True,
        ),
        StrInput(
            name="pix_key_value",
            display_name="PIX Key Value",
            info="Value of the PIX key (email, CPF, CNPJ, phone, or leave empty for RANDOM)",
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
        Output(name="response", display_name="Response", method="create_pix_key"),
    ]
    
    def create_pix_key(self) -> Data:
        """
        Create a PIX key in the P3 Banking API.
        
        Returns:
            Data: Contains the response from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}/pix-dict"
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
            "type": self.pix_key_type,
            "value": self.pix_key_value,
        }
        
        # Log the complete payload being sent to the API
        try:
            payload_json = json.dumps(body, indent=2, ensure_ascii=False)
            self.log(f"Request URL: {url}")
            self.log(f"Request Payload:\n{payload_json}")
        except Exception as e:
            self.log(f"Could not format payload for logging: {e}")
            self.log(f"Request URL: {url}")
            self.log(f"Request Payload: {body}")
        
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
                if "data" in result and isinstance(result["data"], dict):
                    result["error_details"] = result["data"]
            
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

