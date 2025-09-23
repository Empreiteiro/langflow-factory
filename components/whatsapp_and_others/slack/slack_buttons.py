from lfx.custom import Component
from lfx.io import SecretStrInput, StrInput, Output
from lfx.schema import Data
import requests
import json


class SlackApprovalMessageComponent(Component):
    display_name = "Slack Approval"
    description = "Sends an interactive approval message via Slack."
    icon = "Slack"
    name = "SlackApprovalMessageComponent"

    inputs = [
        SecretStrInput(
            name="slack_token",
            display_name="Slack Bot Token",
            required=True,
            password=True,
            info="Slack bot token (starts with 'xoxb-')."
        ),
        StrInput(
            name="channel_id",
            display_name="Channel ID",
            required=True,
            info="Slack channel ID to send the message to."
        ),
        StrInput(
            name="text",
            display_name="Plain Text Message",
            required=False,
            info="Plain text accompanying the message blocks."
        ),
        StrInput(
            name="question_text",
            display_name="Approval Question",
            required=False,
            info="Text asking for approval."
        ),
        StrInput(
            name="approve_label",
            display_name="Approve Button Text",
            required=False,
            info="Text for the Approve button."
        ),
        StrInput(
            name="reject_label",
            display_name="Reject Button Text",
            required=False,
            info="Text for the Reject button."
        )
    ]

    outputs = [
        Output(name="response", display_name="Slack Response", method="send_message_output")
    ]

    field_order = ["slack_token", "channel_id", "text", "question_text", "approve_label", "reject_label"]

    def send_message_output(self) -> Data:
        slack_token = self.slack_token
        if hasattr(slack_token, "get_secret_value"):
            slack_token = slack_token.get_secret_value()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {slack_token}"
        }

        payload = {
            "channel": self.channel_id,
            "text": self.text or "Choose an option:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": self.question_text or "Do you approve this request?"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "action_id": "approve_btn",
                            "text": {
                                "type": "plain_text",
                                "text": self.approve_label or "Approve"
                            },
                            "style": "primary",
                            "value": "approve"
                        },
                        {
                            "type": "button",
                            "action_id": "reject_btn",
                            "text": {
                                "type": "plain_text",
                                "text": self.reject_label or "Reject"
                            },
                            "style": "danger",
                            "value": "reject"
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                url="https://slack.com/api/chat.postMessage",
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise Exception(f"Slack API Error: {result.get('error')}")
            self.status = "Message sent successfully."
            return Data(data=result)
        except Exception as e:
            error_message = f"Error sending message to Slack: {str(e)}"
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})
