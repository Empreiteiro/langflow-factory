"""
P3 PIX Billing Component

This component creates a PIX billing in the P3 Banking API by making a POST request
to the /realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId/pix-billing endpoint.
"""

import json
import requests

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, IntInput, BoolInput
from langflow.schema import Data


class P3PixBillingComponent(Component):
    display_name = "P3 PIX Billing"
    description = "Create a PIX billing in the P3 Banking API"
    icon = "credit-card"
    name = "P3PixBillingComponent"
    
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
            name="txn_currency",
            display_name="Transaction Currency",
            info="Currency code (e.g., '986' for BRL)",
            value="986",
            required=True,
            advanced=True,
        ),
        IntInput(
            name="txn_amount",
            display_name="Transaction Amount",
            info="Transaction amount in cents",
            required=True,
        ),
        BoolInput(
            name="txn_can_amount_change",
            display_name="Can Amount Change",
            info="Whether the transaction amount can be changed",
            value=True,
            required=False,
        ),
        StrInput(
            name="billing_description",
            display_name="Billing Description",
            info="Description of the billing",
            required=True,
        ),
        StrInput(
            name="customer_name",
            display_name="Customer Name",
            info="Full name of the customer",
            required=True,
        ),
        StrInput(
            name="customer_document",
            display_name="Customer Document",
            info="CPF or CNPJ of the customer (numbers only)",
            required=True,
        ),
        StrInput(
            name="customer_email",
            display_name="Customer Email",
            info="Email address of the customer",
            required=True,
        ),
        StrInput(
            name="customer_address_street",
            display_name="Address Street",
            info="Street name",
            required=True,
        ),
        StrInput(
            name="customer_address_number",
            display_name="Address Number",
            info="Street number",
            required=True,
        ),
        StrInput(
            name="customer_address_complement",
            display_name="Address Complement",
            info="Address complement (e.g., apartment, suite)",
            required=False,
        ),
        StrInput(
            name="customer_address_neighborhood",
            display_name="Address Neighborhood",
            info="Neighborhood name",
            required=True,
        ),
        StrInput(
            name="customer_address_postal_code",
            display_name="Address Postal Code",
            info="Postal code (CEP) in format XXXXX-XXX",
            required=True,
        ),
        StrInput(
            name="customer_address_city",
            display_name="Address City",
            info="City name",
            required=True,
        ),
        StrInput(
            name="customer_address_state",
            display_name="Address State",
            info="State abbreviation",
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
        Output(name="response", display_name="Response", method="create_pix_billing"),
    ]
    
    def create_pix_billing(self) -> Data:
        """
        Create a PIX billing in the P3 Banking API.
        
        Returns:
            Data: Contains the response from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}/pix-billing"
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
            "txnCurrency": self.txn_currency,
            "txnAmount": self.txn_amount,
            "txnCanAmountChange": getattr(self, 'txn_can_amount_change', True),
            "description": self.billing_description,
        }
        
        # Build customer information from individual fields
        if not hasattr(self, 'customer_name') or not self.customer_name:
            return Data(
                value={
                    "status": "error",
                    "message": "Customer name is required",
                    "url": url,
                }
            )
        
        if not hasattr(self, 'customer_document') or not self.customer_document:
            return Data(
                value={
                    "status": "error",
                    "message": "Customer document is required",
                    "url": url,
                }
            )
        
        if not hasattr(self, 'customer_email') or not self.customer_email:
            return Data(
                value={
                    "status": "error",
                    "message": "Customer email is required",
                    "url": url,
                }
            )
        
        customer_address = {
            "street": self.customer_address_street,
            "number": self.customer_address_number,
            "neighborhood": self.customer_address_neighborhood,
            "postalCode": self.customer_address_postal_code,
            "city": self.customer_address_city,
            "state": self.customer_address_state,
        }
        
        # Add complement if provided
        if hasattr(self, 'customer_address_complement') and self.customer_address_complement:
            customer_address["complement"] = self.customer_address_complement
        
        body["customer"] = {
            "name": self.customer_name,
            "document": self.customer_document,
            "email": self.customer_email,
            "address": customer_address,
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

