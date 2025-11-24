import time
import requests
import urllib3
from lfx.custom import Component

# Disable SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from lfx.inputs import MessageTextInput, DropdownInput, MultilineInput
from lfx.template import Output
from lfx.schema import Data

class SendMessageThenDocument(Component):
    display_name = "Z-API"
    description = "Sends a message, waits a configurable amount of time, and then sends a document using Z-API."
    icon = "phone"
    name = "SendMessageThenDocument"

    inputs = [
        MessageTextInput(name="zapi_instance", display_name="Instance", required=True),
        MessageTextInput(name="zapi_token", display_name="Token", required=True),
        MessageTextInput(name="zapi_client_token", display_name="Client Token", required=True),
        MessageTextInput(name="phone", display_name="Phone", required=True),
        MessageTextInput(name="message", display_name="Message", required=True),
        MessageTextInput(name="wait_seconds", display_name="Wait Seconds", required=True, tool_mode=True),
        MessageTextInput(name="document", display_name="Document URL", required=True),
        MessageTextInput(name="fileName", display_name="File Name", required=True),
        DropdownInput(name="extension", display_name="Document Extension", options=["pdf"], value="pdf"),
    ]

    outputs = [
        Output(display_name="API Response", name="api_response", method="send_message_then_document"),
    ]

    field_order = ["zapi_instance", "zapi_token", "zapi_client_token", "phone", "message", "wait_seconds", "document", "fileName", "extension"]

    def send_message_then_document(self) -> Data:
        instance = self.zapi_instance
        token = self.zapi_token
        client_token = self.zapi_client_token
        phone = self.phone
        message = self.message
        document = self.document
        fileName = self.fileName
        extension = self.extension

        headers = {
            "Content-Type": "application/json",
            "Client-Token": client_token,
        }

        timeout = 30
        try:
            # Send message
            message_url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-text"
            message_payload = {
                "phone": phone,
                "message": message
            }
            message_response = requests.post(message_url, json=message_payload, headers=headers, verify=False, timeout=timeout)
            message_response.raise_for_status()
            message_result = message_response.json()
            self.log(f"Message sent: {message_result}")

            # Wait for specified seconds
            try:
                wait_seconds = int(self.wait_seconds)
            except ValueError:
                return Data(data={"error": "Invalid wait_seconds value, must be an integer."})

            time.sleep(wait_seconds)

            # Send document
            doc_url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-document/{extension}"
            doc_payload = {
                "phone": phone,
                "document": document,
                "fileName": fileName
            }
            doc_response = requests.post(doc_url, json=doc_payload, headers=headers, verify=False, timeout=timeout)
            doc_response.raise_for_status()
            doc_result = doc_response.json()
            self.log(f"Document sent: {doc_result}")

            return Data(data={"message_response": message_result, "document_response": doc_result})

        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                error_msg = "DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings."
            else:
                error_msg = f"Connection error: {error_str}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "error_type": "connection_error"})
        except requests.exceptions.Timeout:
            error_msg = "Request timeout: The request took longer than 30 seconds to complete."
            self.log(error_msg)
            return Data(data={"error": error_msg, "error_type": "timeout"})
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "error_type": "request_error"})
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            return Data(data={"error": str(e), "error_type": "unexpected_error"})
