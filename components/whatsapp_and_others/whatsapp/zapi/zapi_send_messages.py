import json
import requests
import urllib3
from typing import Any, Dict, List, Optional

# Disable SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from lfx.custom.custom_component.component import Component
from lfx.inputs import (
    MessageTextInput,
    DropdownInput,
    MultilineInput,
    MessageInput,
)
from lfx.io import SecretStrInput, Output
from lfx.schema import Data
from lfx.logging import logger


class ZAPISendMessagesComponent(Component):
    """
    Z-API Send Messages component for sending messages via Z-API services.
    
    This component is focused only on sending different types of messages:
    - Text messages
    - Audio messages
    - Video messages
    - Documents
    - Button lists
    
    Each message type has its own output and method, allowing users to connect
    to the specific action they want to perform.
    """

    display_name: str = "Z-API Send Messages"
    name = "ZAPISendMessages"
    icon = "message-circle"
    description = "Component for sending messages via Z-API (text, audio, video, document, button list)"

    # Base inputs
    inputs = [
        MessageInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger input to connect with flow (not used in processing).",
            required=False,
            advanced=True,
            show=True
        ),

        # Authentication fields
        SecretStrInput(
            name="zapi_instance",
            display_name="Instance",
            info="Z-API instance ID.",
            required=True,
            advanced=True,
            show=True
        ),
        SecretStrInput(
            name="zapi_token",
            display_name="Token",
            info="Z-API authentication token.",
            required=True,
            advanced=True,
            show=True
        ),
        SecretStrInput(
            name="zapi_client_token",
            display_name="Client Token",
            info="Token enviado no header da requisição.",
            required=True,
            advanced=True,
            show=True
        ),
        # Message fields
        MessageTextInput(
            name="phone",
            display_name="Phone",
            info="Recipient phone number in international format.",
            required=True,
            show=False
        ),
        MessageTextInput(
            name="message",
            display_name="Message",
            info="Text message to be sent.",
            show=False
        ),
        MessageTextInput(
            name="audio",
            display_name="Audio URL/Base64",
            info="Audio URL or Base64 to send.",
            show=False
        ),
        MessageTextInput(
            name="video",
            display_name="Video URL",
            info="Video URL to send.",
            show=False
        ),
        MessageTextInput(
            name="caption",
            display_name="Video Caption",
            info="Caption for the video (optional).",
            show=False
        ),
        MessageTextInput(
            name="document", 
            display_name="Document URL", 
            dynamic=True, 
            show=False, 
            tool_mode=True
        ),
        MessageTextInput(
            name="fileName", 
            display_name="File Name", 
            dynamic=True, 
            show=False
        ),
        DropdownInput(
            name="extension",
            display_name="Document Extension",
            options=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"],
            value="pdf",
            dynamic=True,
            show=False,
        ),
        MultilineInput(
            name="buttonList",
            display_name="Button List JSON",
            info="Exemplo: {\"buttons\": [{\"id\": \"1\", \"label\": \"Ótimo\"}, {\"id\": \"2\", \"label\": \"Excelente\"}]}",
            value='{"buttons": [{"id": "1", "label": "Ótimo"}, {"id": "2", "label": "Excelente"}]}',
            dynamic=True,
            show=False,
        ),
    ]

    outputs = [
        Output(display_name="Send Text Message", name="send_text", method="send_text_message"),
        Output(display_name="Send Audio Message", name="send_audio", method="send_audio_message"),
        Output(display_name="Send Video Message", name="send_video", method="send_video_message"),
        Output(display_name="Send Document", name="send_document", method="send_document_message"),
        Output(display_name="Send Button List", name="send_button_list", method="send_button_list_message"),
    ]

    def safe_json_parse(self, json_str):
        """Safely parse JSON string to object."""
        if not json_str:
            return {}
        try:
            if isinstance(json_str, str):
                return json.loads(json_str)
            elif isinstance(json_str, dict):
                return json_str
            else:
                return {}
        except Exception as e:
            self.log(f"Error parsing JSON: {str(e)}")
            return {}

    def _get_secret_value(self, secret_input):
        """Extract secret value from SecretStrInput."""
        if hasattr(secret_input, 'get_secret_value'):
            return secret_input.get_secret_value()
        elif isinstance(secret_input, str):
            return secret_input
        return secret_input

    def send_text_message(self) -> Data:
        """Send text message via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._send_text_message(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            msg = f"Failed to send text message: {e!s}"
            raise ValueError(msg) from e

    def send_audio_message(self) -> Data:
        """Send audio message via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._send_audio_message(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error sending audio message: {e}")
            msg = f"Failed to send audio message: {e!s}"
            raise ValueError(msg) from e

    def send_video_message(self) -> Data:
        """Send video message via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._send_video_message(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error sending video message: {e}")
            msg = f"Failed to send video message: {e!s}"
            raise ValueError(msg) from e

    def send_document_message(self) -> Data:
        """Send document via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._send_document_message(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error sending document: {e}")
            msg = f"Failed to send document: {e!s}"
            raise ValueError(msg) from e

    def send_button_list_message(self) -> Data:
        """Send button list via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._send_button_list_message(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error sending button list: {e}")
            msg = f"Failed to send button list: {e!s}"
            raise ValueError(msg) from e

    def _send_text_message(self, instance, token, headers):
        """Send text message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-text"
        payload = {
            "phone": self.phone,
            "message": self.message
        }
        timeout = 30
        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                raise ValueError("DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings.") from e
            raise ValueError(f"Connection error: {error_str}") from e
        except requests.exceptions.Timeout:
            raise ValueError("Request timeout: The request took longer than 30 seconds to complete.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {str(e)}") from e

    def _send_audio_message(self, instance, token, headers):
        """Send audio message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-audio"
        payload = {
            "phone": self.phone,
            "audio": self.audio,
            "viewOnce": False,
            "waveform": True
        }
        timeout = 30
        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                raise ValueError("DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings.") from e
            raise ValueError(f"Connection error: {error_str}") from e
        except requests.exceptions.Timeout:
            raise ValueError("Request timeout: The request took longer than 30 seconds to complete.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {str(e)}") from e

    def _send_video_message(self, instance, token, headers):
        """Send video message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-video"
        payload = {
            "phone": self.phone,
            "video": self.video,
            "caption": getattr(self, 'caption', ''),
            "viewOnce": False
        }
        timeout = 30
        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                raise ValueError("DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings.") from e
            raise ValueError(f"Connection error: {error_str}") from e
        except requests.exceptions.Timeout:
            raise ValueError("Request timeout: The request took longer than 30 seconds to complete.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {str(e)}") from e

    def _send_document_message(self, instance, token, headers):
        """Send document via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-document/{self.extension}"
        payload = {
            "phone": self.phone,
            "document": self.document,
            "fileName": self.fileName
        }
        timeout = 30
        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                raise ValueError("DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings.") from e
            raise ValueError(f"Connection error: {error_str}") from e
        except requests.exceptions.Timeout:
            raise ValueError("Request timeout: The request took longer than 30 seconds to complete.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {str(e)}") from e

    def _send_button_list_message(self, instance, token, headers):
        """Send button list via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-button-list"
        payload = {
            "phone": self.phone,
            "message": self.message,
            "buttonList": self.safe_json_parse(self.buttonList)
        }
        timeout = 30
        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                raise ValueError("DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings.") from e
            raise ValueError(f"Connection error: {error_str}") from e
        except requests.exceptions.Timeout:
            raise ValueError("Request timeout: The request took longer than 30 seconds to complete.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {str(e)}") from e

