"""
P3 Access Token Component

This component authenticates with the P3 Identity API using client credentials
and returns an access token for use with protected APIs.
"""

import json
import requests
from requests.auth import HTTPBasicAuth

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data


class P3GetAccessTokenComponent(Component):
    display_name = "P3 Get Access Token"
    description = "Authenticate with P3 Identity API and get access token"
    icon = "key"
    name = "P3GetAccessTokenComponent"
    
    inputs = [
        SecretStrInput(
            name="client_id",
            display_name="Client ID",
            info="Client ID for authentication (used as username in Basic Auth)",
            required=True,
        ),
        SecretStrInput(
            name="client_secret",
            display_name="Client Secret",
            info="Client secret for authentication (used as password in Basic Auth)",
            required=True,
        ),
    ]
    
    outputs = [
        Output(name="response", display_name="Response", method="get_access_token"),
    ]
    
    def get_access_token(self) -> Data:
        """
        Authenticate with P3 Identity API and get access token.
        
        Returns:
            Data: Contains the access token and refresh token from the API
        """
        # Build the URL
        base_url = "https://api.identity.v2.portao3.com.br".rstrip('/')
        url = f"{base_url}/auth/sign-in"
        
        # Get client credentials
        client_id = self.client_id
        if hasattr(self.client_id, 'get_secret_value'):
            client_id = self.client_id.get_secret_value()
        elif isinstance(self.client_id, str):
            client_id = self.client_id
        
        client_secret = self.client_secret
        if hasattr(self.client_secret, 'get_secret_value'):
            client_secret = self.client_secret.get_secret_value()
        elif isinstance(self.client_secret, str):
            client_secret = self.client_secret
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
        }
        
        # Prepare request body
        body = {
            "grantType": "client_credentials",
        }
        
        # Prepare Basic Authentication
        auth = HTTPBasicAuth(client_id, client_secret)
        
        try:
            # Make POST request with Basic Auth
            response = requests.post(
                url,
                auth=auth,
                headers=headers,
                json=body,
                timeout=30
            )
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                
                # Build result with success/error status
                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "status_code": response.status_code,
                        "access_token": response_data.get("accessToken"),
                        "refresh_token": response_data.get("refreshToken"),
                        "data": response_data,
                        "url": url,
                    }
                else:
                    result = {
                        "status": "error",
                        "status_code": response.status_code,
                        "data": response_data,
                        "url": url,
                        "message": f"Authentication failed with status {response.status_code}",
                    }
                    self.log(f"Authentication failed: {response.status_code} - {response_data}")
                    
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, return raw response
                result = {
                    "status": "error" if response.status_code >= 400 else "success",
                    "status_code": response.status_code,
                    "raw_response": response.text,
                    "url": url,
                    "message": "Failed to parse JSON response",
                }
            
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
