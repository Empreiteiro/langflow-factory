from langflow.custom import Component
from langflow.io import (
    StrInput,
    MultilineInput,
    SecretStrInput,
    DropdownInput,
    Output,
)
from langflow.schema import Data
from openai import OpenAI


class OpenAIAgentComponent(Component):
    display_name = "OpenAI Agent"
    description = "Execute prompts using OpenAI's Chat Completions API."
    icon = "bot"
    name = "OpenAIAgentComponent"
    beta = True

    field_order = ["api_key", "model", "prompt"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="OpenAI API Key",
            info="Your OpenAI API key for authentication.",
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the OpenAI model to use.",
            options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            value="gpt-4o-mini",
        ),
        MultilineInput(
            name="prompt",
            display_name="Prompt",
            info="The text or instructions to send to the OpenAI model.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Agent Response", method="run_agent"),
    ]

    def run_agent(self) -> Data:
        """
        Execute the prompt using OpenAI's Chat Completions API and return the response as Data.
        """
        try:
            # Initialize OpenAI client with the provided API key
            client = OpenAI(api_key=self.api_key)

            # Call the chat completions endpoint with the specified model and prompt
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.prompt}],
            )

            # Extract the text content from the response
            message = response.choices[0].message.content

            # Return the result encapsulated in a Data object
            self.status = "Prompt executed successfully."
            return Data(text=message)

        except Exception as e:
            # In case of error, log and return the error message
            error_msg = f"Error executing OpenAI agent: {e}"
            self.log(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})
