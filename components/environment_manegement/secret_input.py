from lfx.base.io.text import TextComponent
from lfx.io import MultilineInput, Output, SecretStrInput
from lfx.schema.message import Message


class SecretInputComponent(TextComponent):
    display_name = "Secret Input"
    description = "Allows the selection of a secret to be generated as output.."
    documentation: str = "https://docs.langflow.org/components-io#text-input"
    icon = "type"
    name = "SecretInput"

    inputs = [
        SecretStrInput(
            name="input_value",
            display_name="Secret",
            info="Secret to be passed as input.",
        ),
    ]
    outputs = [
        Output(display_name="Output Text", name="text", method="text_response"),
    ]

    def text_response(self) -> Message:
        return Message(
            text=self.input_value,
        )
