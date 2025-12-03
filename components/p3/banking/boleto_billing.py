"""
P3 Boleto Billing Component

This component creates a boleto (billing slip) in the P3 Banking API by making a POST request
to the /realms/:realmId/organizations/:organizationId/accounts/:accountId/wallets/:walletId/boleto-billing endpoint.
"""

import json
import requests
from datetime import datetime, timedelta

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, MultilineInput, IntInput, FloatInput, DropdownInput
from langflow.schema import Data


class P3BoletoBillingComponent(Component):
    display_name = "P3 Boleto Billing"
    description = "Create a boleto (billing slip) in the P3 Banking API"
    icon = "file-text"
    name = "P3BoletoBillingComponent"
    
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
        IntInput(
            name="txn_max_amount",
            display_name="Transaction Max Amount",
            info="Maximum transaction amount in cents (0 if not applicable)",
            value=0,
            required=False,
            advanced=True,
        ),
        IntInput(
            name="txn_min_amount",
            display_name="Transaction Min Amount",
            info="Minimum transaction amount in cents (0 if not applicable)",
            value=0,
            required=False,
            advanced=True,
        ),
        DropdownInput(
            name="txn_divergent_amount_type",
            display_name="Divergent Amount Type",
            options=["NOT_ALLOW_DIFFERENT_AMOUNT", "ALLOW_DIFFERENT_AMOUNT"],
            value="NOT_ALLOW_DIFFERENT_AMOUNT",
            info="Type of divergent amount allowed",
            required=False,
            advanced=True,
        ),
        MultilineInput(
            name="txn_discount_amount",
            display_name="Discount Amount (JSON)",
            info="JSON array of discount amounts. Example: [{\"date\": \"2024-12-18\", \"amount\": 5000, \"amountType\": \"FIXED_AMOUNT_UNTIL_INFORMED_DATE\"}]",
            required=False,
        ),
        FloatInput(
            name="txn_fine_percent",
            display_name="Fine Percent",
            info="Fine percentage amount. Must be >= 0.01 if provided.",
            required=False,
        ),
        FloatInput(
            name="txn_interest_percent",
            display_name="Interest Percent",
            info="Interest percentage amount. Must be >= 0.01 if provided.",
            required=False,
        ),
        StrInput(
            name="due_date",
            display_name="Due Date",
            info="Due date in format YYYY-MM-DD",
            required=True,
        ),
        StrInput(
            name="expires_at",
            display_name="Expires At",
            info="Expiration date in format YYYY-MM-DD",
            required=True,
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
        Output(name="response", display_name="Response", method="create_boleto"),
    ]
    
    def create_boleto(self) -> Data:
        """
        Create a boleto (billing slip) in the P3 Banking API.
        
        Returns:
            Data: Contains the response from the API
        """
        # Build the URL with path parameters
        base_url = "https://api.banking.v2.portao3.com.br".rstrip('/')
        url = (
            f"{base_url}/realms/{self.realm_id}/"
            f"organizations/{self.organization_id}/"
            f"accounts/{self.account_id}/"
            f"wallets/{self.wallet_id}/boleto-billing"
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
            "txnMaxAmount": getattr(self, 'txn_max_amount', 0) or 0,
            "txnMinAmount": getattr(self, 'txn_min_amount', 0) or 0,
            "txnDivergentAmountType": getattr(self, 'txn_divergent_amount_type', 'NOT_ALLOW_DIFFERENT_AMOUNT') or 'NOT_ALLOW_DIFFERENT_AMOUNT',
            "dueDate": self.due_date,
            "expiresAt": self.expires_at,
            "description": self.billing_description,
        }
        
        # Parse discount amount if provided
        if hasattr(self, 'txn_discount_amount') and self.txn_discount_amount:
            try:
                discount_data = json.loads(self.txn_discount_amount)
                body["txnDiscountAmount"] = discount_data if isinstance(discount_data, list) else [discount_data]
            except json.JSONDecodeError as e:
                self.log(f"Warning: Invalid JSON in discount amount: {e}")
                body["txnDiscountAmount"] = []
        
        # Calculate date for fine and interest (dueDate + 1 day)
        try:
            due_date_obj = datetime.strptime(self.due_date, "%Y-%m-%d")
            fine_interest_date = (due_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError as e:
            error_msg = f"Invalid due date format. Expected YYYY-MM-DD: {e}"
            self.log(error_msg)
            return Data(
                value={
                    "status": "error",
                    "message": error_msg,
                    "url": url,
                }
            )
        
        # Build fine amount if provided and valid (>= 0.01)
        if hasattr(self, 'txn_fine_percent') and self.txn_fine_percent is not None:
            fine_value = float(self.txn_fine_percent)
            if fine_value >= 0.01:
                body["txnFineAmount"] = {
                    "date": fine_interest_date,
                    "amount": fine_value,
                    "amountType": "PERCENT"
                }
            else:
                self.log(f"Warning: Fine percent value {fine_value} is less than 0.01, skipping txnFineAmount")
        
        # Build interest amount if provided and valid (>= 0.01)
        if hasattr(self, 'txn_interest_percent') and self.txn_interest_percent is not None:
            interest_value = float(self.txn_interest_percent)
            if interest_value >= 0.01:
                body["txnInterestAmount"] = {
                    "date": fine_interest_date,
                    "amount": interest_value,
                    "amountType": "PERCENT_POINT_PER_MONTH_WORKING_DAYS"
                }
            else:
                self.log(f"Warning: Interest percent value {interest_value} is less than 0.01, skipping txnInterestAmount")
        
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

