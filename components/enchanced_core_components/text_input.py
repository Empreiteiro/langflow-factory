from langflow.base.io.text import TextComponent
from langflow.io import MultilineInput, Output, HandleInput
from langflow.schema.message import Message


class TextInputComponent(TextComponent):
    display_name = "Text Input"
    description = "Get user text inputs."
    documentation: str = "https://docs.langflow.org/components-io#text-input"
    icon = "type"
    name = "TextInput"

    inputs = [
        HandleInput(
            name="trigger",
            display_name="Trigger",
            info="Input to trigger the text input execution. Accepts text, data, or dataframe.",
            input_types=["Text", "Data", "DataFrame"],
            required=False,
            advanced=True,
        ),
        MultilineInput(
            name="input_value",
            display_name="Text",
            info="Text to be passed as input.",
        ),
    ]
    outputs = [
        Output(display_name="Output Text", name="text", method="text_response"),
    ]

    def text_response(self) -> Message:
        return Message(
            text=self.input_value,
        )
