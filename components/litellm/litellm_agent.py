"""LiteLLM Agent Component (Non-Streaming) for LangFlow.

Enhanced agent component using non-streaming HTTP calls to preserve provider metadata
(citations, search results, usage info, etc.). Supports dynamic property extraction
and tool calling with LiteLLM proxy servers.
"""

import json
from typing import Any, Optional

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr, Field

from lfx.components.helpers import CurrentDateComponent
from lfx.components.langchain_utilities.tool_calling import ToolCallingAgentComponent
from lfx.inputs.inputs import BoolInput, DictInput, SecretStrInput, StrInput
from lfx.io import MultilineInput, Output
from lfx.log.logger import logger
from lfx.schema.message import Message

class LiteLLMAgentComponent(ToolCallingAgentComponent):
    """Agent component that uses LiteLLM proxy for language model capabilities.

    This component allows you to connect to a LiteLLM proxy server and use any model
    supported by LiteLLM, including OpenAI, Anthropic, Google, and many others.
    
    Uses non-streaming mode to preserve citations, search_results, and other metadata.
    """

    display_name: str = "LiteLLM Agent"
    description: str = "LiteLLM agent using non-streaming HTTP calls to preserve provider metadata."
    documentation: str = "https://docs.litellm.ai/docs/langchain/"
    icon = "🚅"
    beta = True
    name = "litellm_agent"
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
        StrInput(
            name="extract_top_level_properties",
            display_name="Extract Top-Level Properties",
            info="Comma-separated list of response properties to extract and append to content. Example: 'citations,search_results' or 'cost,usage'. Leave empty to skip extraction.",
            value="",
            advanced=True,
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
        """Execute the agent with the input and return the response."""
        try:
            llm_model, chat_history, self.tools = await self.get_agent_requirements()

            if isinstance(llm_model, LiteLLMChatNonStreaming):
                llm_model.tools = self.tools or []

            self.set(
                llm=llm_model,
                tools=self.tools or [],
                chat_history=chat_history,
                input_value=self.input_value,
                system_prompt=self.system_prompt,
            )

            agent = self.create_agent_runnable()
            return await self.run_agent(agent)

        except (ValueError, TypeError, KeyError) as e:
            await logger.aerror(f"{type(e).__name__}: {e!s}")
            raise
        except Exception as e:
            await logger.aerror(f"Unexpected error: {e!s}")
            raise

    def build_model(self) -> ChatOpenAI:
        """Build LiteLLMChatNonStreaming model and configure property extraction."""
        api_key = SecretStr(self.api_key).get_secret_value() if self.api_key else None

        props = []
        if self.extract_top_level_properties and self.extract_top_level_properties.strip():
            props = [p.strip() for p in self.extract_top_level_properties.split(",") if p.strip()]

        extra_body = {}
        if self.model_params:
            if isinstance(self.model_params, dict):
                extra_body = {k: v for k, v in self.model_params.items() if k}
            else:
                for entry in self.model_params:
                    if isinstance(entry, dict):
                        extra_body.update({k: v for k, v in entry.items() if k})

        model = LiteLLMChatNonStreaming(
            model=self.model_name,
            api_key=api_key,
            base_url=self.base_url,
            streaming=False,
        )
        model.top_level_properties = props
        if extra_body:
            model.extra_body = extra_body
        return model

class LiteLLMChatNonStreaming(ChatOpenAI):
    """ChatOpenAI override using non-streaming HTTP calls to preserve API response metadata."""
    
    top_level_properties: list[str] = Field(default_factory=list)
    tools: list[StructuredTool] = Field(default_factory=list)

    @staticmethod
    def _convert_tool_to_openai_format(tool: StructuredTool) -> dict:
        """Convert a LangChain StructuredTool to OpenAI function calling format."""
        schema = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, "model_json_schema") else {}

        parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
        }
        if "required" in schema:
            parameters["required"] = schema["required"]

        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "No description provided",
                "parameters": parameters,
            },
        }

    async def _astream(self, *args, **kwargs):
        """Force non-streaming by converting streaming calls to _agenerate."""
        result = await self._agenerate(*args, **kwargs)
        if result.generations:
            yield result.generations[0]

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Make direct HTTP call to LiteLLM API with stream=False to preserve metadata."""
        api_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                api_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                api_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, AIMessage):
                api_messages.append({"role": "assistant", "content": msg.content})
            else:
                api_messages.append({"role": "user", "content": str(msg.content)})

        payload = {
            "model": self.model_name,
            "messages": api_messages,
            "stream": False,
        }

        if stop:
            payload["stop"] = stop
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        if self.tools:
            payload["tools"] = [self._convert_tool_to_openai_format(tool) for tool in self.tools]
            payload["tool_choice"] = "auto"

        if hasattr(self, "extra_body") and self.extra_body:
            payload.update(self.extra_body)

        api_key = self.openai_api_key
        if hasattr(api_key, 'get_secret_value'):
            api_key = api_key.get_secret_value()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self.openai_api_base}/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()

        choice = response_data["choices"][0]
        message_data = choice.get("message", {})
        content = message_data.get("content") or ""
        additional_kwargs = {}

        for prop_name in self.top_level_properties:
            if prop_name in response_data:
                prop_value = response_data[prop_name]
                additional_kwargs[prop_name] = prop_value
                prop_json = json.dumps(prop_value, indent=2)
                content += f"\n\n<{prop_name}>\n{prop_json}\n</{prop_name}>"

        for key, value in message_data.items():
            if key not in ["role", "content"] and key not in additional_kwargs:
                additional_kwargs[key] = value

        ai_message = AIMessage(content=content, additional_kwargs=additional_kwargs)
        generation = ChatGeneration(message=ai_message, generation_info=response_data.get("usage", {}))

        return ChatResult(generations=[generation])