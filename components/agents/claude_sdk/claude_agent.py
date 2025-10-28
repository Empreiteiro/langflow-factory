from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, DropdownInput
from langflow.schema import Data
import os
from anthropic import Anthropic


class ClaudeAgentComponent(Component):
    display_name = "Claude Agent"
    description = "Executes queries to the Claude model using the official Anthropic SDK."
    icon = "robot"
    name = "ClaudeAgent"
    beta = True

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Anthropic API Key",
            info="Your Anthropic API key. If not provided, uses ANTHROPIC_API_KEY environment variable.",
            required=False,
        ),
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="Input text for the Claude agent.",
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="The Claude model to use.",
            options=["claude-4-5-sonnet-latest", "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            value="claude-4-5-sonnet-latest",
            required=True,
        ),
        StrInput(
            name="max_tokens",
            display_name="Max Tokens",
            info="Maximum number of tokens to generate.",
            value="1024",
            required=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Claude Response", method="run_claude_query"),
    ]

    field_order = ["api_key", "model", "max_tokens", "prompt"]

    def run_claude_query(self) -> Data:
        """Executes a query to the Claude model and returns the response."""
        try:
            # Initialize the Anthropic client
            # Check if api_key is provided as input
            if hasattr(self, 'api_key') and self.api_key:
                api_key = self.api_key
                self.log("Using API key from component input.")
            else:
                # Try to get from environment variable
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if api_key:
                    self.log("Using API key from ANTHROPIC_API_KEY environment variable.")
                else:
                    error_message = "API key is required. Please provide an Anthropic API key in the component input or set ANTHROPIC_API_KEY environment variable."
                    self.status = error_message
                    self.log(error_message)
                    return Data(data={"error": error_message})
            
            # Validate API key format (Anthropic keys start with sk-)
            if not api_key or not api_key.strip():
                error_message = "API key is empty. Please provide a valid Anthropic API key."
                self.status = error_message
                self.log(error_message)
                return Data(data={"error": error_message})
                
            if not api_key.startswith("sk-"):
                error_message = "Invalid API key format. Anthropic API keys should start with 'sk-'. Please check your API key."
                self.status = error_message
                self.log(error_message)
                return Data(data={"error": error_message})
            
            client = Anthropic(api_key=api_key.strip())
            
            # Parse max_tokens
            try:
                max_tokens = int(self.max_tokens) if self.max_tokens else 1024
            except ValueError:
                max_tokens = 1024
            
            self.status = f"Sending request to {self.model}..."
            self.log(f"Calling Claude API with model: {self.model}, max_tokens: {max_tokens}")
            
            # Make the API call
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": self.prompt}
                ]
            )
            
            # Extract the text content from the response
            if message.content and len(message.content) > 0:
                response_text = message.content[0].text
            else:
                response_text = "No response generated."
            
            self.status = "Claude query completed successfully."
            return Data(data={"text": response_text})
            
        except Exception as e:
            # Provide more helpful error messages
            error_str = str(e)
            if "401" in error_str or "authentication" in error_str.lower():
                error_message = "Authentication failed. Please check your API key is valid and starts with 'sk-'. You can get your API key from https://console.anthropic.com/"
            elif "invalid x-api-key" in error_str.lower():
                error_message = "Invalid API key. Please ensure you're using a valid Anthropic API key from https://console.anthropic.com/"
            else:
                error_message = f"Failed to execute Claude agent: {e}"
            
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})
