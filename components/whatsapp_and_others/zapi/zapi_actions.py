import json
import requests
from typing import Any, Dict, List, Optional

from langflow.custom.custom_component.component import Component
from langflow.inputs import (
    MessageTextInput,
    DropdownInput,
    SortableListInput,
    MultilineInput,
    MessageInput,
    BoolInput,
    IntInput,
)
from langflow.io import SecretStrInput, Output
from langflow.schema import Data
from langflow.schema.dataframe import DataFrame
from langflow.logging import logger
import pandas as pd


class ZAPIActionsComponent(Component):
    """
    Z-API Actions component for interacting with Z-API services.
    
    This component serves as an example of how to create a component with separate actions
    in Langflow. Each action appears as a separate output with its own method.
    
    STEPS TO CREATE A COMPONENT WITH SEPARATE ACTIONS:
    
    1. Define multiple outputs with different methods:
       outputs = [
           Output(display_name="Action 1", name="action1", method="method1"),
           Output(display_name="Action 2", name="action2", method="method2"),
           ...
       ]
    
    2. Create a separate method for each action:
       def method1(self) -> Data:
           # Action 1 logic
           return Data(data={"result": result})
       
       def method2(self) -> Data:
           # Action 2 logic
           return Data(data={"result": result})
    
    3. Each output with a different method will appear as a separate action in Langflow
    
    4. Remove any action selection inputs - users just connect the desired output
    
    5. Each method should handle its own authentication, validation, and error handling
    
    KEY POINTS:
    - Each output = one action in Langflow
    - Each method = one specific operation
    - No need for action selection dropdown
    - Users connect the output they want to execute
    - Follow the pattern of other components like StructuredOutputComponent
    """

    display_name: str = "Z-API Actions"
    name = "ZAPIActions"
    icon = "message-circle"
    description = "Component for all Z-API operations with actions-based structure"

    # Z-API specific actions
    _actions_data: dict = {
        "ZAPI_SEND_TEXT": {
            "display_name": "Send Text Message",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "phone",
                "message",
            ],
        },
        "ZAPI_SEND_AUDIO": {
            "display_name": "Send Audio Message",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "phone",
                "audio",
            ],
        },
        "ZAPI_SEND_VIDEO": {
            "display_name": "Send Video Message",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "phone",
                "video",
                "caption",
            ],
        },
        "ZAPI_SEND_DOCUMENT": {
            "display_name": "Send Document",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "phone",
                "document",
                "fileName",
                "extension",
            ],
        },
        "ZAPI_SEND_BUTTON_LIST": {
            "display_name": "Send Button List",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "phone",
                "message",
                "buttonList",
            ],
        },
        "ZAPI_GET_GROUPS": {
            "display_name": "Get Groups",
            "action_fields": [
                "zapi_instance",
                "zapi_token",
                "zapi_client_token",
                "page",
                "pageSize",
            ],
            "get_result_field": True,
            "result_field": "groups",
        },
    }
    
    _all_fields = {field for action_data in _actions_data.values() for field in action_data["action_fields"]}
    _bool_variables = set()
    _default_tools = set()

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
        IntInput(
            name="page",
            display_name="Page",
            info="Page number for pagination (used for Get Groups operation).",
            value=1,
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="pageSize",
            display_name="Page Size",
            info="Number of groups per page (used for Get Groups operation).",
            value=10,
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
        Output(display_name="Get Groups", name="get_groups", method="get_groups_action"),
        Output(display_name="Groups DataFrame", name="groups_dataframe", method="get_groups_dataframe"),
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

    def get_groups_action(self) -> Data:
        """Get groups via Z-API."""
        try:
            # Extract secret values
            instance = self._get_secret_value(self.zapi_instance)
            token = self._get_secret_value(self.zapi_token)
            client_token = self._get_secret_value(self.zapi_client_token)

            headers = {
                "Content-Type": "application/json",
                "Client-Token": client_token
            }

            result = self._get_groups(instance, token, headers)
            return Data(data={"api_response": result})

        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            msg = f"Failed to get groups: {e!s}"
            raise ValueError(msg) from e

    def _send_text_message(self, instance, token, headers):
        """Send text message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-text"
        payload = {
            "phone": self.phone,
            "message": self.message
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _send_audio_message(self, instance, token, headers):
        """Send audio message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-audio"
        payload = {
            "phone": self.phone,
            "audio": self.audio,
            "viewOnce": False,
            "waveform": True
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _send_video_message(self, instance, token, headers):
        """Send video message via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-video"
        payload = {
            "phone": self.phone,
            "video": self.video,
            "caption": getattr(self, 'caption', ''),
            "viewOnce": False
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _send_document_message(self, instance, token, headers):
        """Send document via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-document/{self.extension}"
        payload = {
            "phone": self.phone,
            "document": self.document,
            "fileName": self.fileName
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _send_button_list_message(self, instance, token, headers):
        """Send button list via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-button-list"
        payload = {
            "phone": self.phone,
            "message": self.message,
            "buttonList": self.safe_json_parse(self.buttonList)
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _get_groups(self, instance, token, headers):
        """Get groups via Z-API."""
        url = f"https://api.z-api.io/instances/{instance}/token/{token}/groups"
        page = getattr(self, 'page', 1)
        page_size = getattr(self, 'pageSize', 10)
        
        # Ensure values are integers
        try:
            page = int(page) if page is not None and page != "" else 1
            page_size = int(page_size) if page_size is not None and page_size != "" else 10
        except (ValueError, TypeError):
            page = 1
            page_size = 10
        
        payload = {
            "page": page,
            "pageSize": page_size
        }
        response = requests.get(url, params=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Process groups response
        self._process_groups_response(result)
        return {
            "groups": result.get('groups', []),
            "total": result.get('total', 0),
            "page": page,
            "pageSize": page_size,
            "raw_response": result
        }

    def _process_groups_response(self, result):
        """Process groups response and store for DataFrame generation."""
        if isinstance(result, dict):
            groups_data = result.get('groups', [])
            if not isinstance(groups_data, list):
                groups_data = [groups_data] if groups_data else []
            
            self._groups_result = {
                "groups": groups_data,
                "total": len(groups_data),
                "raw_response": result
            }
        else:
            self._groups_result = {
                "groups": [],
                "total": 0,
                "raw_response": result
            }

    def get_groups_dataframe(self) -> DataFrame:
        """Generate DataFrame from groups data."""
        try:
            if not hasattr(self, '_groups_result') or not self._groups_result:
                return DataFrame([])
            
            groups_data = self._groups_result.get('groups', [])
            if not groups_data:
                return DataFrame([])
            
            # Normalize groups data
            normalized_groups = []
            for group in groups_data:
                if isinstance(group, dict):
                    flat_group = self._flatten_dict(group)
                    normalized_groups.append(flat_group)
                else:
                    basic_group = {
                        'group_data': str(group),
                        'group_type': type(group).__name__
                    }
                    normalized_groups.append(basic_group)
            
            if not normalized_groups:
                return DataFrame([])
            
            # Create DataFrame
            df = pd.DataFrame(normalized_groups)
            
            # Format columns for better readability
            df = self._format_dataframe_columns(df)
            
            # Add metadata
            metadata = {
                'total_groups': self._groups_result.get('total', 0),
                'groups_in_page': len(normalized_groups)
            }
            
            for key, value in metadata.items():
                df[key] = value
            
            return DataFrame(df)
            
        except Exception as e:
            self.log(f"Error creating DataFrame: {str(e)}")
            return DataFrame([])

    def _flatten_dict(self, data, parent_key='', sep='_'):
        """Flatten nested dictionaries for better DataFrame structure."""
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                if v and isinstance(v[0], dict):
                    flattened_items = []
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            flattened = self._flatten_dict(item, f"{new_key}_{i}", sep=sep)
                            flattened_items.append(flattened)
                    if flattened_items:
                        combined = {}
                        for item in flattened_items:
                            combined.update(item)
                        items.extend(combined.items())
                else:
                    items.append((new_key, ', '.join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _format_dataframe_columns(self, df):
        """Format DataFrame columns for better readability."""
        if df.empty:
            return df
        
        column_mapping = {
            'id': 'group_id',
            'name': 'group_name',
            'description': 'group_description',
            'created_at': 'created_date',
            'updated_at': 'updated_date',
            'member_count': 'total_members',
            'admin_count': 'total_admins'
        }
        
        existing_columns = df.columns.tolist()
        rename_dict = {col: column_mapping[col] for col in existing_columns if col in column_mapping}
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        return df

    def set_default_tools(self):
        """Set default tools for the component."""
        self._default_tools = {
            "ZAPI_SEND_TEXT",
            "ZAPI_GET_GROUPS",
        } 