from langflow.custom import Component
from langflow.io import MessageInput, DropdownInput, Output
from langflow.schema import Data
from langflow.schema.message import Message
import tiktoken

class TokenCounter(Component):
    display_name = "Token Counter"
    description = "Counts the number of tokens in a string or message using OpenAI tokenizer."
    icon = "mdi-counter"
    name = "TokenCounter"

    inputs = [
        MessageInput(
            name="text",
            display_name="Input Text or Message",
            info="The text or message object to tokenize. Accepts raw strings or Message objects.",
            required=True,
        ),
        DropdownInput(
            name="model_name",
            display_name="Model Name",
            info="Select the model to determine the correct tokenizer.",
            options=[
                "gpt-4o",
                "gpt-4",
                "gpt-4-32k",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "text-davinci-003",
                "text-embedding-ada-002"
            ],
            value="gpt-4o"
        ),
    ]

    outputs = [
        Output(name="token_count", display_name="Token Count", method="count_tokens")
    ]

    field_order = ["text", "model_name"]

    def count_tokens(self) -> Message:
        try:
            if isinstance(self.text, Message):
                input_text = self.text.text
            elif isinstance(self.text, str):
                input_text = self.text
            else:
                raise TypeError(f"Unsupported input type: {type(self.text)}")

            try:
                enc = tiktoken.encoding_for_model(self.model_name)
            except Exception:
                self.log(f"Model '{self.model_name}' not recognized. Falling back to 'cl100k_base'.")
                enc = tiktoken.get_encoding("cl100k_base")

            num_tokens = len(enc.encode(input_text))
            self.status = f"{num_tokens} tokens found"
            
            return Message(
                text=str(num_tokens),
                metadata={
                    "token_count": num_tokens,
                    "model_name": self.model_name,
                    "input_length": len(input_text)
                }
            )

        except Exception as e:
            error_msg = f"Error while counting tokens: {e}"
            self.status = error_msg
            self.log(error_msg)
            return Message(text="0", metadata={"error": error_msg})
