"""LiteLLM Agent Component for LangFlow.

Agent component that connects to a LiteLLM proxy server for multi-provider LLM support.
Supports streaming mode with automatic tool calling and callback handling.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from lfx.components.helpers import CurrentDateComponent
from lfx.components.langchain_utilities.tool_calling import ToolCallingAgentComponent
from lfx.inputs.inputs import BoolInput, DictInput, SecretStrInput, StrInput
from lfx.io import MultilineInput, Output
from lfx.log.logger import logger
from lfx.schema.message import Message


class LiteLLMAgentStreamComponent(ToolCallingAgentComponent):
    """LiteLLM Agent Component (Streaming)."""

    display_name: str = "LiteLLM Agent (Stream)"
    description: str = "LiteLLM agent component using streaming HTTP calls for real-time responses."
    documentation: str = "https://docs.litellm.ai/docs/langchain/"
    icon: str = "🚅"
    priority: int = 100
    name: str = "litellm_agent_stream"
    beta = True
    version = "1.0.0"

    inputs = [
        StrInput(
            name="base_url",
            display_name="LiteLLM Base URL",
            info="The base URL of the LiteLLM API (e.g., http://localhost:8000).",
            value="http://localhost:8000",
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="API key for the LiteLLM proxy.",
            required=True,
        ),
        StrInput(
            name="model_name",
            display_name="Model Name",
            info="The model name to use (e.g., gpt-4.1, claude-3.5, llama-3).",
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="Agent Instructions",
            info="System Prompt: Initial instructions and context provided to guide the agent's behavior.",
            value="You are a helpful assistant that can use tools to answer questions and perform tasks.",
            advanced=False,
        ),
        *ToolCallingAgentComponent.get_base_inputs(),
        DictInput(
            name="model_params",
            display_name="Model Parameters",
            is_list=True,
            advanced=True,
            info="Provider-specific parameters to pass through to LiteLLM.",
        ),
        BoolInput(
            name="add_current_date_tool",
            display_name="Current Date",
            advanced=True,
            info="If true, will add a tool to the agent that returns the current date.",
            value=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="message_response"),
    ]

    async def get_agent_requirements(self):
        """Get the agent requirements for the agent."""
        llm_model = self.build_model()
        if llm_model is None:
            msg = "No language model selected. Please choose a model to proceed."
            raise ValueError(msg)

        chat_history = []

        if not isinstance(self.tools, list):
            self.tools = []

        if self.add_current_date_tool:
            current_date_tool = (await CurrentDateComponent(**self.get_base_args()).to_toolkit()).pop(0)

            if not isinstance(current_date_tool, StructuredTool):
                msg = "CurrentDateComponent must be converted to a StructuredTool"
                raise TypeError(msg)
            self.tools.append(current_date_tool)

        self.set_tools_callbacks(self.tools, self._get_shared_callbacks())

        return llm_model, chat_history, self.tools

    async def message_response(self) -> Message:
        """Process the input message and return a response.

        Returns:
            Message: The agent's response as a Message object.

        Raises:
            ValueError: If the language model is not properly configured.
            TypeError: If tool conversion fails.
        """
        try:
            llm_model, chat_history, self.tools = await self.get_agent_requirements()

            self.set(
                llm=llm_model,
                tools=self.tools or [],
                chat_history=chat_history,
                input_value=self.input_value,
                system_prompt=self.system_prompt,
            )

            agent = self.create_agent_runnable()
            result = await self.run_agent(agent)

        except (ValueError, TypeError, KeyError) as e:
            await logger.aerror(f"{type(e).__name__}: {e!s}")
            raise
        except Exception as e:
            await logger.aerror(f"Unexpected error: {e!s}")
            raise
        else:
            return result

    def build_model(self) -> ChatOpenAI:
        """Build and configure the ChatOpenAI model for LiteLLM.

        Returns:
            ChatOpenAI: Configured language model instance.
        """
        api_key = SecretStr(self.api_key).get_secret_value() if self.api_key else None

        # Merge and filter model parameters, removing empty keys
        extra_body = {}
        if self.model_params:
            if isinstance(self.model_params, dict):
                extra_body = {k: v for k, v in self.model_params.items() if k}
            else:
                for entry in self.model_params:
                    if isinstance(entry, dict):
                        extra_body.update({k: v for k, v in entry.items() if k})

        kwargs = {
            "model": self.model_name,
            "api_key": api_key,
            "base_url": self.base_url,
        }

        # Only include extra_body if it has actual content
        if extra_body:
            kwargs["extra_body"] = extra_body

        return ChatOpenAI(**kwargs)

