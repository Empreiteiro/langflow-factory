from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, MessageInput, Output
from langflow.schema import Data
import requests

class TelegramMessageSender(Component):
    display_name = "Telegram Message Sender"
    description = "Sends a message via Telegram Bot API."
    icon = "telegram"
    name = "TelegramMessageSender"

    inputs = [
        SecretStrInput(
            name="bot_token",
            display_name="Bot Token",
            info="Your Telegram bot token.",
            required=True,
        ),
        MessageInput(
            name="chat_id",
            display_name="Chat ID",
            info="The Telegram chat ID to send the message to. Can be fixed or received from another component.",
            required=True,
        ),
        MessageInput(
            name="message",
            display_name="Message",
            info="The message to send.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="send_message"),
    ]

    def send_message(self) -> Data:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        message_text = self.message.text if hasattr(self.message, "text") else str(self.message)
        payload = {"chat_id": self.chat_id, "text": message_text}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return Data(data=response.json())
        except requests.exceptions.RequestException as e:
            self.log(f"Error sending message: {e}")
            return Data(data={"error": str(e)})