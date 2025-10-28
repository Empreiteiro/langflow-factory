from langflow.custom import Component
from langflow.io import StrInput, Output, SecretStrInput, DropdownInput, BoolInput
from langflow.schema import Data
import asyncio
from claude_agent_sdk._internal.client import InternalClient
from claude_agent_sdk.types import ClaudeAgentOptions


class ClaudeCodeAgentComponent(Component):
    display_name = "Claude Code Agent"
    description = (
        "Creates and maintains a persistent instance of the Claude Code SDK for "
        "stateful interactions and multiple queries."
    )
    icon = "bot"
    name = "ClaudeCodeAgent"
    beta = True

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Claude API Key",
            info="Your Claude (Anthropic) API key.",
            required=True,
        ),
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="Input text to be sent to the Claude Code agent.",
            required=True,
        ),
        StrInput(
            name="system_prompt",
            display_name="System Prompt",
            info="Defines the agent's behavior (optional).",
            required=False,
        ),
        StrInput(
            name="working_directory",
            display_name="Working Directory",
            info="Path to the directory where Claude Code will operate.",
            required=False,
        ),
        DropdownInput(
            name="permission_mode",
            display_name="Permission Mode",
            info="Defines tool permission behavior.",
            options=[
                "default",
                "acceptEdits",
                "bypassPermissions",
            ],
            value="default",
        ),
        BoolInput(
            name="reuse_instance",
            display_name="Reuse Existing Instance",
            info="If enabled, reuses the Claude Code client in subsequent calls.",
            value=True,
        ),
        BoolInput(
            name="debug",
            display_name="Debug",
            info="Shows detailed execution logs.",
            value=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Claude Code Response", method="run_agent"),
    ]

    field_order = [
        "api_key",
        "prompt",
        "system_prompt",
        "working_directory",
        "permission_mode",
        "reuse_instance",
        "debug",
    ]

    def _get_or_create_client(self):
        """Returns a persistent instance of InternalClient."""
        client_key = f"{self._id}_claude_client"
        client = self.ctx.get(client_key)

        if not client or not self.reuse_instance:
            client = InternalClient()
            self.update_ctx({client_key: client})
            if self.debug:
                self.log("New Claude Code Client instance created.")
        elif self.debug:
            self.log("Reusing existing Claude Code Client instance.")

        return client

    def run_agent(self) -> Data:
        """Executes the prompt using a persistent Claude Code instance."""

        async def _run(prompt: str):
            try:
                client = self._get_or_create_client()
                options = ClaudeAgentOptions(
                    system_prompt=self.system_prompt or "",
                    cwd=self.working_directory or None,
                    permission_mode=self.permission_mode or "default",
                )

                if self.debug:
                    self.log(f"Executing query: {prompt[:100]}...")
                    self.log(f"Options: {options}")

                response_text = ""
                async for message in client.process_query(prompt=prompt, options=options):
                    response_text += str(message)

                return response_text
            except Exception as e:
                return f"Error processing query with Claude Code: {e}"

        try:
            result = asyncio.run(_run(self.prompt))
            self.status = "Execution completed successfully."
            return Data(data={"text": result})
        except RuntimeError:
            # Fixes the case where Langflow already has an active loop
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(_run(self.prompt))
                self.status = "Execution completed successfully (existing loop)."
                return Data(data={"text": result})
            except Exception as e:
                error_message = f"Error executing with existing loop: {e}"
                self.log(error_message)
                return Data(data={"error": error_message})
        except Exception as e:
            error_message = f"Failed to execute Claude Code agent: {e}"
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})
