from langflow.base.data.utils import IMG_FILE_TYPES, TEXT_FILE_TYPES
from langflow.base.io.chat import ChatComponent
from langflow.inputs.inputs import BoolInput
from langflow.io import (
    DropdownInput,
    FileInput,
    MessageTextInput,
    MultilineInput,
    Output,
    TabInput,
)
from langflow.schema.message import Message
from langflow.schema.data import Data
from langflow.utils.constants import (
    MESSAGE_SENDER_AI,
    MESSAGE_SENDER_NAME_USER,
    MESSAGE_SENDER_USER,
)


class ChatInput(ChatComponent):
    display_name = "Chat Input"
    description = "Get chat inputs from the Playground."
    documentation: str = "https://docs.langflow.org/components-io#chat-input"
    icon = "MessagesSquare"
    name = "ChatInput"
    minimized = True

    inputs = [
        MultilineInput(
            name="input_value",
            display_name="Input Text",
            value="",
            info="Message to be passed as input.",
            input_types=[],
        ),
        BoolInput(
            name="should_store_message",
            display_name="Store Messages",
            info="Store the message in the history.",
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="sender",
            display_name="Sender Type",
            options=[MESSAGE_SENDER_AI, MESSAGE_SENDER_USER],
            value=MESSAGE_SENDER_USER,
            info="Type of sender.",
            advanced=True,
        ),
        MessageTextInput(
            name="sender_name",
            display_name="Sender Name",
            info="Name of the sender.",
            value=MESSAGE_SENDER_NAME_USER,
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name="Session ID",
            info="The session ID of the chat. If empty, the current session ID parameter will be used.",
            advanced=True,
        ),
        FileInput(
            name="files",
            display_name="Files",
            file_types=TEXT_FILE_TYPES + IMG_FILE_TYPES,
            info="Files to be sent with the message.",
            advanced=True,
            is_list=True,
            temp_file=True,
        ),
        MessageTextInput(
            name="background_color",
            display_name="Background Color",
            info="The background color of the icon.",
            advanced=True,
        ),
        MessageTextInput(
            name="chat_icon",
            display_name="Icon",
            info="The icon of the message.",
            advanced=True,
        ),
        MessageTextInput(
            name="text_color",
            display_name="Text Color",
            info="The text color of the name",
            advanced=True,
        ),
    ]
    outputs = [
        Output(display_name="Chat Message", name="message", method="message_response"),
    ]

    async def message_response(self) -> Message:
        background_color = self.background_color
        text_color = self.text_color
        icon = self.chat_icon

        message = await Message.create(
            text=self.input_value,
            sender=self.sender,
            sender_name=self.sender_name,
            session_id=self.session_id,
            files=self.files,
            properties={
                "background_color": background_color,
                "text_color": text_color,
                "icon": icon,
            },
        )
        if self.session_id and isinstance(message, Message) and self.should_store_message:
            stored_message = await self.send_message(
                message,
            )
            self.message.value = stored_message
            message = stored_message

        self.status = message
        return message


class FlexibleChatInput(ChatComponent):
    display_name = "Flexible Chat/Data Input"
    description = "Input component that can emit either a chat Message or structured Data (JSON)."
    documentation: str = "https://docs.langflow.org/components-io#chat-input"
    icon = "MessagesSquare"
    name = "FlexibleChatInput"
    minimized = True

    inputs = [
        TabInput(
            name="input_type",
            display_name="Input Type",
            options=["Text", "Data"],
            value="Text",
            info="Choose the type of input to emit.",
            real_time_refresh=True,
        ),
        MultilineInput(
            name="input_value",
            display_name="Input Text",
            value="",
            info="Message text to be sent when Input Type is Text.",
            input_types=[],
            dynamic=True,
            show=True,
        ),
        MultilineInput(
            name="data_value",
            display_name="Data (JSON)",
            value="{}",
            info="JSON content to emit when Input Type is Data.",
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="should_store_message",
            display_name="Store Messages",
            info="Store the message in the history (only for Text mode).",
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="sender",
            display_name="Sender Type",
            options=[MESSAGE_SENDER_AI, MESSAGE_SENDER_USER],
            value=MESSAGE_SENDER_USER,
            info="Type of sender (Text mode only).",
            advanced=True,
        ),
        MessageTextInput(
            name="sender_name",
            display_name="Sender Name",
            info="Name of the sender (Text mode only).",
            value=MESSAGE_SENDER_NAME_USER,
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name="Session ID",
            info="Session ID of the chat (Text mode only).",
            advanced=True,
        ),
        FileInput(
            name="files",
            display_name="Files",
            file_types=TEXT_FILE_TYPES + IMG_FILE_TYPES,
            info="Files to be sent with the message (Text mode only).",
            advanced=True,
            is_list=True,
            temp_file=True,
        ),
        MessageTextInput(
            name="background_color",
            display_name="Background Color",
            info="Background color of the icon (Text mode only).",
            advanced=True,
        ),
        MessageTextInput(
            name="chat_icon",
            display_name="Icon",
            info="Icon of the message (Text mode only).",
            advanced=True,
        ),
        MessageTextInput(
            name="text_color",
            display_name="Text Color",
            info="Text color of the name (Text mode only).",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Chat Message", name="message", method="message_response"),
        Output(display_name="Data", name="data", method="data_response"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "input_type":
            # TabInput provides a string value
            input_type = field_value if isinstance(field_value, str) else "Text"

            # Toggle visibility of inputs to match selected type
            is_text = input_type == "Text"
            # Primary fields
            build_config["input_value"]["show"] = is_text
            build_config["data_value"]["show"] = not is_text

            # Text-mode only fields
            for f in [
                "should_store_message",
                "sender",
                "sender_name",
                "session_id",
                "files",
                "background_color",
                "chat_icon",
                "text_color",
            ]:
                if f in build_config:
                    build_config[f]["show"] = is_text

        return build_config

    def update_outputs(self, frontend_node: dict, field_name: str, field_value):
        # Dynamically expose only the relevant output
        if field_name == "input_type":
            input_type = field_value if isinstance(field_value, str) else "Text"
            frontend_node["outputs"] = []
            if input_type == "Text":
                frontend_node["outputs"].append(
                    Output(display_name="Chat Message", name="message", method="message_response")
                )
            else:
                frontend_node["outputs"].append(
                    Output(display_name="Data", name="data", method="data_response")
                )
        return frontend_node

    async def message_response(self) -> Message:
        # Only used when input_type == "Text"
        background_color = self.background_color
        text_color = self.text_color
        icon = self.chat_icon

        message = await Message.create(
            text=self.input_value,
            sender=self.sender,
            sender_name=self.sender_name,
            session_id=self.session_id,
            files=self.files,
            properties={
                "background_color": background_color,
                "text_color": text_color,
                "icon": icon,
            },
        )
        if self.session_id and isinstance(message, Message) and self.should_store_message:
            stored_message = await self.send_message(message)
            self.message.value = stored_message
            message = stored_message

        self.status = message
        return message

    def data_response(self) -> Data:
        # Only used when input_type == "Data"
        try:
            raw = self.data_value or "{}"
            import json
            parsed = json.loads(raw)
            return Data(data=parsed)
        except Exception as e:
            return Data(data={"error": f"Invalid JSON: {e}", "raw": self.data_value})
