import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

from lfx.custom import Component
from lfx.io import (
    StrInput, 
    MessageTextInput,
    SecretStrInput,
    IntInput,
    BoolInput,
    Output,
    DataInput,
    DropdownInput,
    TableInput
)
from lfx.inputs import SortableListInput
from lfx.schema import Data


class WhatsAppEvolutionComponent(Component):
    display_name = "WhatsApp Evolution"
    description = "Unified component for all WhatsApp Evolution API actions"
    icon = "message-circle"
    name = "WhatsAppEvolutionComponent"

    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the WhatsApp action. Connect any component output here to trigger the action.",
            required=False,
        ),
        MessageTextInput(
            name="base_url",
            display_name="API Base URL",
            info="Evolution API base URL (e.g., http://example.com:8080)",
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Evolution API key for authentication",
            required=True,
        ),
        MessageTextInput(
            name="instance_id",
            display_name="Instance ID",
            info="Evolution API instance identifier",
            required=True,
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="List of actions to perform with WhatsApp Evolution API.",
            options=[
                {"name": "Send Text Message", "icon": "message-square"},
                {"name": "Send Media", "icon": "image"},
                {"name": "Send Audio", "icon": "mic"},
                {"name": "Send Location", "icon": "map-pin"},
                {"name": "Send List", "icon": "list"},
                {"name": "Send Poll", "icon": "bar-chart-2"},
                {"name": "Send Sticker", "icon": "smile"},
                {"name": "Send Status", "icon": "circle"},
                {"name": "Send Reaction", "icon": "heart"},
                {"name": "Find Contacts", "icon": "users"},
                {"name": "Find Chats", "icon": "messages-square"},
                {"name": "Find Messages", "icon": "search"},
                {"name": "Check Phone", "icon": "check"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        
        # Common inputs (shown for most actions)
        MessageTextInput(
            name="number",
            display_name="Recipient Number",
            info="WhatsApp ID of the recipient (e.g., 5511999999999@s.whatsapp.net)",
            show=False,
        ),
        
        # Text message inputs
        MessageTextInput(
            name="text",
            display_name="Message Text",
            info="The text message to send",
            show=False,
        ),
        
        # Media inputs
        MessageTextInput(
            name="media_url",
            display_name="Media URL",
            info="URL of the media file to send",
            show=False,
        ),
        DropdownInput(
            name="media_type",
            display_name="Media Type",
            info="Type of media to send",
            options=["image", "video", "document"],
            value="image",
            show=False,
        ),
        MessageTextInput(
            name="media_caption",
            display_name="Caption",
            info="Caption for the media file",
            show=False,
        ),
        MessageTextInput(
            name="filename",
            display_name="Filename",
            info="Custom filename for the media (optional)",
            show=False,
        ),
        
        # Audio inputs
        MessageTextInput(
            name="audio_url",
            display_name="Audio URL",
            info="URL of the audio file to send",
            show=False,
        ),
        BoolInput(
            name="audio_ptt",
            display_name="Voice Message",
            info="Send as voice message (PTT)",
            show=False,
            value=True,
        ),
        
        # Location inputs
        MessageTextInput(
            name="latitude",
            display_name="Latitude",
            info="Latitude coordinate of the location",
            show=False,
        ),
        MessageTextInput(
            name="longitude",
            display_name="Longitude",
            info="Longitude coordinate of the location",
            show=False,
        ),
        MessageTextInput(
            name="location_name",
            display_name="Location Name",
            info="Name of the location",
            show=False,
        ),
        MessageTextInput(
            name="address",
            display_name="Address",
            info="Address of the location",
            show=False,
        ),
        
        # List inputs
        MessageTextInput(
            name="list_title",
            display_name="List Title",
            info="Title of the list message",
            show=False,
        ),
        MessageTextInput(
            name="list_description",
            display_name="List Description",
            info="Description of the list",
            show=False,
        ),
        MessageTextInput(
            name="button_text",
            display_name="Button Text",
            info="Text to display on the button",
            show=False,
        ),
        MessageTextInput(
            name="footer_text",
            display_name="Footer Text",
            info="Text to display in the footer",
            show=False,
        ),
        TableInput(
            name="list_items",
            display_name="List Items",
            info="Add rows to your list. Rows with the same section title will be grouped together.",
            show=False,
            value=[],
            table_schema=[
                {"name": "section_title", "display_name": "Section Title", "type": "str"},
                {"name": "item_title", "display_name": "Item Title", "type": "str"},
                {"name": "item_description", "display_name": "Item Description", "type": "str"},
                {"name": "item_id", "display_name": "Item ID", "type": "str"},
            ],
        ),
        
        # Poll inputs
        MessageTextInput(
            name="poll_name",
            display_name="Poll Question",
            info="The main text/question of the poll",
            show=False,
        ),
        TableInput(
            name="poll_options",
            display_name="Poll Options",
            info="Options for the poll",
            show=False,
            value=[],
            table_schema=[
                {"name": "option_text", "display_name": "Option Text", "type": "str"},
            ],
        ),
        IntInput(
            name="selectable_count",
            display_name="Selectable Count",
            info="Number of options that can be selected (default: 1)",
            show=False,
            value=1,
        ),
        
        # Sticker inputs
        MessageTextInput(
            name="sticker_url",
            display_name="Sticker URL",
            info="URL of the sticker file to send",
            show=False,
        ),
        
        # Status inputs
        DropdownInput(
            name="status_type",
            display_name="Status Type",
            info="Type of status to send",
            options=["text", "image", "video"],
            value="text",
            show=False,
        ),
        MessageTextInput(
            name="status_content",
            display_name="Status Content",
            info="Content for the status (text or media URL)",
            show=False,
        ),
        MessageTextInput(
            name="status_background_color",
            display_name="Background Color",
            info="Background color for text status (hex color)",
            show=False,
        ),
        MessageTextInput(
            name="status_caption",
            display_name="Status Caption", 
            info="Caption for media status",
            show=False,
        ),
        
        # Reaction inputs
        MessageTextInput(
            name="message_id",
            display_name="Message ID",
            info="ID of the message to react to",
            show=False,
        ),
        MessageTextInput(
            name="emoji",
            display_name="Emoji",
            info="Emoji to react with",
            show=False,
        ),
        
        # Search inputs
        MessageTextInput(
            name="remote_jid",
            display_name="Remote JID",
            info="WhatsApp ID to search from (e.g., 5551999999999@s.whatsapp.net)",
            show=False,
        ),
        MessageTextInput(
            name="numbers_to_check",
            display_name="Phone Numbers",
            info="List of phone numbers to check (one per line)",
            show=False,
            is_list=True,
        ),
        
        # Advanced options (shown for applicable actions)
        MessageTextInput(
            name="quoted_message_id",
            display_name="Quoted Message ID",
            info="ID of the message to quote (optional)",
            show=False,
            advanced=True,
        ),
        IntInput(
            name="delay",
            display_name="Delay",
            info="Optional delay in milliseconds",
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="mentions_everyone",
            display_name="Mention Everyone",
            info="Whether to mention all participants",
            show=False,
            advanced=True,
        ),
        MessageTextInput(
            name="mentioned",
            display_name="Mentioned Numbers",
            info="List of WhatsApp IDs to mention (comma-separated)",
            show=False,
            advanced=True,
            is_list=True,
        ),
        BoolInput(
            name="link_preview",
            display_name="Link Preview",
            info="Whether to show link previews in the message",
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="show_typing",
            display_name="Show Typing",
            info="Show typing indicator before sending message",
            show=False,
            advanced=True,
        ),
        IntInput(
            name="typing_delay",
            display_name="Typing Delay",
            info="How long to show typing indicator (in milliseconds)",
            show=False,
            advanced=True,
            value=3000,
        ),
    ]

    outputs = [
        Output(name="evolution_result", display_name="Result", method="run_action")
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update the build configuration based on selected action"""
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        # Field mapping for each action
        field_map = {
            "Send Text Message": ["number", "text", "quoted_message_id", "delay", "mentions_everyone", "mentioned", "link_preview", "show_typing", "typing_delay"],
            "Send Media": ["number", "media_url", "media_type", "media_caption", "filename", "quoted_message_id", "delay", "show_typing", "typing_delay"],
            "Send Audio": ["number", "audio_url", "audio_ptt", "quoted_message_id", "delay", "show_typing", "typing_delay"],
            "Send Location": ["number", "latitude", "longitude", "location_name", "address", "quoted_message_id", "delay", "show_typing", "typing_delay"],
            "Send List": ["number", "list_title", "list_description", "button_text", "footer_text", "list_items", "quoted_message_id", "delay"],
            "Send Poll": ["number", "poll_name", "poll_options", "selectable_count", "quoted_message_id", "delay"],
            "Send Sticker": ["number", "sticker_url", "quoted_message_id", "delay", "show_typing", "typing_delay"],
            "Send Status": ["status_type", "status_content", "status_background_color", "status_caption"],
            "Send Reaction": ["message_id", "emoji", "number"],
            "Find Contacts": ["remote_jid"],
            "Find Chats": [],
            "Find Messages": ["remote_jid"],
            "Check Phone": ["numbers_to_check"],
        }

        # Hide all dynamic fields first
        all_dynamic_fields = [
            "number", "text", "media_url", "media_type", "media_caption", "filename", "audio_url", "audio_ptt",
            "latitude", "longitude", "location_name", "address", "list_title", "list_description", "button_text",
            "footer_text", "list_items", "poll_name", "poll_options", "selectable_count", "sticker_url",
            "status_type", "status_content", "status_background_color", "status_caption", "message_id", "emoji",
            "remote_jid", "numbers_to_check", "quoted_message_id", "delay", "mentions_everyone", "mentioned",
            "link_preview", "show_typing", "typing_delay"
        ]
        
        for field_name in all_dynamic_fields:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def log(self, message: str):
        """Custom logging method"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

    def run_action(self) -> Data:
        """Execute the selected WhatsApp Evolution action"""
        # Validate required inputs
        if not hasattr(self, 'api_key') or not self.api_key:
            return Data(data={"error": "API key is required"})
        
        if not hasattr(self, 'action') or not self.action:
            return Data(data={"error": "Action is required"})

        if not hasattr(self, 'base_url') or not self.base_url:
            return Data(data={"error": "Base URL is required"})

        if not hasattr(self, 'instance_id') or not self.instance_id:
            return Data(data={"error": "Instance ID is required"})

        # Extract action name from the selected action
        action_name = None
        if isinstance(self.action, list) and len(self.action) > 0:
            action_name = self.action[0].get("name")
        elif isinstance(self.action, dict):
            action_name = self.action.get("name")
        
        if not action_name:
            return Data(data={"error": "Invalid action selected"})

        self.log(f"Executing WhatsApp Evolution action: {action_name}")

        # Route to appropriate action method
        try:
            if action_name == "Send Text Message":
                return self._send_text_message()
            elif action_name == "Send Media":
                return self._send_media()
            elif action_name == "Send Audio":
                return self._send_audio()
            elif action_name == "Send Location":
                return self._send_location()
            elif action_name == "Send List":
                return self._send_list()
            elif action_name == "Send Poll":
                return self._send_poll()
            elif action_name == "Send Sticker":
                return self._send_sticker()
            elif action_name == "Send Status":
                return self._send_status()
            elif action_name == "Send Reaction":
                return self._send_reaction()
            elif action_name == "Find Contacts":
                return self._find_contacts()
            elif action_name == "Find Chats":
                return self._find_chats()
            elif action_name == "Find Messages":
                return self._find_messages()
            elif action_name == "Check Phone":
                return self._check_phone()
            else:
                return Data(data={"error": f"Unsupported action: {action_name}"})
                
        except Exception as e:
            error_msg = f"Error executing {action_name}: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        api_key_value = self.api_key
        if hasattr(self.api_key, 'get_secret_value'):
            api_key_value = self.api_key.get_secret_value()
        elif isinstance(self.api_key, str):
            api_key_value = self.api_key
        
        return {
            "apikey": api_key_value,
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Data:
        """Make API request to Evolution API"""
        base_url = self.base_url.rstrip('/')
        url = f"{base_url}{endpoint}"
        headers = self._get_headers()
        
        self.log(f"Making request to: {url}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            self.log(f"Request successful")
            return Data(data=result)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request error: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _send_text_message(self) -> Data:
        """Send a text message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'text') or not self.text:
            return Data(data={"error": "Message text is required"})

        payload = {
            "number": self.number,
            "text": self.text
        }
        
        # Add optional fields
        self._add_optional_fields(payload, [
            "delay", "mentions_everyone", "mentioned", "link_preview"
        ])
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        # Handle typing presence
        if hasattr(self, 'show_typing') and self.show_typing:
            self._send_typing_presence()

        endpoint = f"/message/sendText/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_media(self) -> Data:
        """Send a media message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'media_url') or not self.media_url:
            return Data(data={"error": "Media URL is required"})

        payload = {
            "number": self.number,
            "media": self.media_url
        }
        
        # Add optional fields
        self._add_optional_fields(payload, [
            "media_caption", "filename", "delay"
        ], field_mapping={"media_caption": "caption"})
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        # Handle typing presence
        if hasattr(self, 'show_typing') and self.show_typing:
            self._send_typing_presence()

        # Determine endpoint based on media type
        media_type = getattr(self, 'media_type', 'image')
        if media_type == "video":
            endpoint = f"/message/sendMedia/{self.instance_id}"
        elif media_type == "document":
            endpoint = f"/message/sendMedia/{self.instance_id}"
        else:  # default to image
            endpoint = f"/message/sendMedia/{self.instance_id}"

        return self._make_request(endpoint, payload)

    def _send_audio(self) -> Data:
        """Send an audio message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'audio_url') or not self.audio_url:
            return Data(data={"error": "Audio URL is required"})

        payload = {
            "number": self.number,
            "audio": self.audio_url
        }
        
        # Add PTT flag if specified
        if hasattr(self, 'audio_ptt') and self.audio_ptt:
            payload["ptt"] = True
        
        # Add optional fields
        self._add_optional_fields(payload, ["delay"])
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        # Handle typing presence
        if hasattr(self, 'show_typing') and self.show_typing:
            self._send_typing_presence()

        endpoint = f"/message/sendWhatsAppAudio/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_location(self) -> Data:
        """Send a location message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'latitude') or not self.latitude:
            return Data(data={"error": "Latitude is required"})
        if not hasattr(self, 'longitude') or not self.longitude:
            return Data(data={"error": "Longitude is required"})

        payload = {
            "number": self.number,
            "latitude": float(self.latitude),
            "longitude": float(self.longitude)
        }
        
        # Add optional fields
        self._add_optional_fields(payload, [
            "location_name", "address", "delay"
        ], field_mapping={"location_name": "name"})
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        # Handle typing presence
        if hasattr(self, 'show_typing') and self.show_typing:
            self._send_typing_presence()

        endpoint = f"/message/sendLocation/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_list(self) -> Data:
        """Send a list message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'list_title') or not self.list_title:
            return Data(data={"error": "List title is required"})
        # Check if list_items exists and has data
        list_items_data = getattr(self, 'list_items', [])
        if hasattr(self.list_items, 'data'):
            list_items_data = self.list_items.data
        if not isinstance(list_items_data, list):
            list_items_data = []
        if not list_items_data:
            return Data(data={"error": "List items are required"})

        # Process list items (already validated above)
        sections = {}
        
        for item in list_items_data:
            section_title = item.get('section_title', 'Default Section')
            if section_title not in sections:
                sections[section_title] = []
            
            sections[section_title].append({
                "title": item.get('item_title', ''),
                "description": item.get('item_description', ''),
                "rowId": item.get('item_id', f"item_{len(sections[section_title])}")
            })

        # Build sections array
        sections_array = []
        for section_title, rows in sections.items():
            sections_array.append({
                "title": section_title,
                "rows": rows
            })

        payload = {
            "number": self.number,
            "title": self.list_title,
            "description": getattr(self, 'list_description', ''),
            "buttonText": getattr(self, 'button_text', 'Select'),
            "footerText": getattr(self, 'footer_text', ''),
            "sections": sections_array
        }
        
        # Add optional fields
        self._add_optional_fields(payload, ["delay"])
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        endpoint = f"/message/sendList/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_poll(self) -> Data:
        """Send a poll message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'poll_name') or not self.poll_name:
            return Data(data={"error": "Poll question is required"})
        # Check if poll_options exists and has data
        poll_options_data = getattr(self, 'poll_options', [])
        if hasattr(self.poll_options, 'data'):
            poll_options_data = self.poll_options.data
        if not isinstance(poll_options_data, list):
            poll_options_data = []
        if not poll_options_data:
            return Data(data={"error": "Poll options are required"})

        # Process poll options (already validated above)
        options = []
        
        for option in poll_options_data:
            options.append(option.get('option_text', ''))

        payload = {
            "number": self.number,
            "name": self.poll_name,
            "selectableCount": getattr(self, 'selectable_count', 1),
            "values": options
        }
        
        # Add optional fields
        self._add_optional_fields(payload, ["delay"])
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        endpoint = f"/message/sendPoll/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_sticker(self) -> Data:
        """Send a sticker message"""
        if not hasattr(self, 'number') or not self.number:
            return Data(data={"error": "Recipient number is required"})
        if not hasattr(self, 'sticker_url') or not self.sticker_url:
            return Data(data={"error": "Sticker URL is required"})

        payload = {
            "number": self.number,
            "sticker": self.sticker_url
        }
        
        # Add optional fields
        self._add_optional_fields(payload, ["delay"])
        
        # Add quoted message if provided
        if hasattr(self, 'quoted_message_id') and self.quoted_message_id:
            payload["quoted"] = {"key": {"id": self.quoted_message_id}}

        # Handle typing presence
        if hasattr(self, 'show_typing') and self.show_typing:
            self._send_typing_presence()

        endpoint = f"/message/sendSticker/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_status(self) -> Data:
        """Send a status message"""
        if not hasattr(self, 'status_type') or not self.status_type:
            return Data(data={"error": "Status type is required"})
        if not hasattr(self, 'status_content') or not self.status_content:
            return Data(data={"error": "Status content is required"})

        payload = {
            "type": self.status_type,
            "content": self.status_content
        }
        
        # Add optional fields based on status type
        if self.status_type == "text" and hasattr(self, 'status_background_color') and self.status_background_color:
            payload["backgroundColor"] = self.status_background_color
        
        if self.status_type in ["image", "video"] and hasattr(self, 'status_caption') and self.status_caption:
            payload["caption"] = self.status_caption

        endpoint = f"/message/sendStatus/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_reaction(self) -> Data:
        """Send a reaction to a message"""
        if not hasattr(self, 'message_id') or not self.message_id:
            return Data(data={"error": "Message ID is required"})
        if not hasattr(self, 'emoji') or not self.emoji:
            return Data(data={"error": "Emoji is required"})

        payload = {
            "reactionMessage": {
                "key": {"id": self.message_id},
                "reaction": self.emoji
            }
        }

        endpoint = f"/message/sendReaction/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _find_contacts(self) -> Data:
        """Find contacts"""
        base_url = self.base_url.rstrip('/')
        endpoint = f"{base_url}/chat/findContacts/{self.instance_id}"
        headers = self._get_headers()
        
        # Add remote_jid as query parameter if provided
        params = {}
        if hasattr(self, 'remote_jid') and self.remote_jid:
            params['where'] = json.dumps({"remoteJid": self.remote_jid})
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            self.log("Contacts retrieved successfully")
            return Data(data=result)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request error: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _find_chats(self) -> Data:
        """Find chats"""
        base_url = self.base_url.rstrip('/')
        endpoint = f"{base_url}/chat/findChats/{self.instance_id}"
        headers = self._get_headers()
        
        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            self.log("Chats retrieved successfully")
            return Data(data=result)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request error: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _find_messages(self) -> Data:
        """Find messages"""
        base_url = self.base_url.rstrip('/')
        endpoint = f"{base_url}/chat/findMessages/{self.instance_id}"
        headers = self._get_headers()
        
        # Add remote_jid as query parameter if provided
        params = {}
        if hasattr(self, 'remote_jid') and self.remote_jid:
            params['where'] = json.dumps({"key.remoteJid": self.remote_jid})
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            self.log("Messages retrieved successfully")
            return Data(data=result)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request error: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def _check_phone(self) -> Data:
        """Check if phone numbers exist on WhatsApp"""
        if not hasattr(self, 'numbers_to_check') or not self.numbers_to_check:
            return Data(data={"error": "Phone numbers are required"})

        # Process numbers list
        numbers = []
        if isinstance(self.numbers_to_check, list):
            numbers = self.numbers_to_check
        elif isinstance(self.numbers_to_check, str):
            numbers = [num.strip() for num in self.numbers_to_check.split('\n') if num.strip()]

        payload = {"numbers": numbers}

        endpoint = f"/chat/whatsappNumbers/{self.instance_id}"
        return self._make_request(endpoint, payload)

    def _send_typing_presence(self):
        """Send typing presence indicator"""
        try:
            payload = {
                "number": self.number,
                "presence": "composing"
            }
            
            endpoint = f"/chat/sendPresence/{self.instance_id}"
            headers = self._get_headers()
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}{endpoint}"
            
            requests.post(url, headers=headers, json=payload)
            
            # Wait for typing delay
            typing_delay = getattr(self, 'typing_delay', 3000)
            import time
            time.sleep(typing_delay / 1000)  # Convert to seconds
            
        except Exception as e:
            self.log(f"Error sending typing presence: {str(e)}")

    def _add_optional_fields(self, payload: Dict[str, Any], fields: List[str], field_mapping: Dict[str, str] = None):
        """Add optional fields to payload if they exist"""
        if field_mapping is None:
            field_mapping = {}
        
        for field in fields:
            if hasattr(self, field) and getattr(self, field):
                payload_key = field_mapping.get(field, field)
                value = getattr(self, field)
                
                # Handle special field transformations
                if field == "mentions_everyone":
                    payload["mentionsEveryOne"] = value
                elif field == "mentioned" and isinstance(value, list):
                    payload["mentioned"] = value
                elif field == "link_preview":
                    payload["linkPreview"] = value
                else:
                    payload[payload_key] = value 
