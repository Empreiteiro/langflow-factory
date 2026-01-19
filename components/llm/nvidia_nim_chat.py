from typing import Any

from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput, MessageTextInput
from lfx.io import DropdownInput, MessageInput, MultilineInput, SecretStrInput, SliderInput


class NIMChatOpenAI(ChatOpenAI):
    """ChatOpenAI wrapper that strips/merges system messages for NIM compatibility."""

    def _normalize_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        system_parts: list[str] = []
        normalized: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role") or "user"
            content = message.get("content") or ""

            if role == "system":
                if content:
                    system_parts.append(str(content))
                continue

            if role not in ("user", "assistant"):
                role = "user"

            if system_parts:
                content = "\n\n".join(system_parts) + ("\n\n" + str(content) if content else "")
                system_parts = []
                role = "user"

            if not str(content).strip():
                continue

            if not normalized and role == "assistant":
                role = "user"

            if normalized and normalized[-1]["role"] == role:
                normalized[-1]["content"] = f"{normalized[-1]['content']}\n\n{content}"
            else:
                normalized.append({"role": role, "content": str(content)})

        if system_parts:
            system_blob = "\n\n".join(system_parts)
            if normalized and normalized[-1]["role"] == "user":
                normalized[-1]["content"] = f"{normalized[-1]['content']}\n\n{system_blob}"
            else:
                normalized.append({"role": "user", "content": system_blob})

        return normalized

    def _get_request_payload(self, input_: Any, **kwargs: Any) -> dict[str, Any]:
        payload = super()._get_request_payload(input_, **kwargs)
        messages = payload.get("messages")
        if isinstance(messages, list):
            payload["messages"] = self._normalize_messages(messages)
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        return payload


class NVIDIANIMChatComponent(LCModelComponent):
    display_name = "NVIDIA NIM Chat"
    description = "Generic NVIDIA NIM chat completion component with model selection."
    icon = "NVIDIA"
    name = "NVIDIANIMChat"
    category = "models"

    MODEL_OPTIONS = [
        "abacusai/dracarys-llama-3.1-70b-instruct",
        "deepseek-ai/deepseek-r1-distill-qwen-32b",
        "google/gemma-3-1b-it",
        "ibm/granite-3_3-8b-instruct",
        "meta/llama-3.3-70b-instruct",
    ]

    inputs = [
        DropdownInput(
            name="model",
            display_name="Model",
            options=MODEL_OPTIONS,
            value=MODEL_OPTIONS[0],
            info="NVIDIA NIM model to use.",
            required=True,
        ),
        MessageTextInput(
            name="base_url",
            display_name="NIM Base URL",
            value="https://integrate.api.nvidia.com/v1",
            info="Base URL for NVIDIA NIM APIs.",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        SecretStrInput(
            name="auth_token",
            display_name="NIM API Key",
            info="API key for NVIDIA NIM.",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        MessageInput(
            name="input_value",
            display_name="Input",
            info="The input text to send to the model.",
        ),
        MultilineInput(
            name="system_message",
            display_name="System Message",
            info="A system message that helps set the behavior of the assistant.",
            advanced=False,
        ),
        BoolInput(
            name="stream",
            display_name="Stream",
            info="Whether to stream the response.",
            value=False,
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name="Temperature",
            value=0.1,
            info="Controls randomness in responses.",
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:
        if not self.auth_token:
            msg = "NIM API key is required."
            raise ValueError(msg)

        return NIMChatOpenAI(
            model_name=self.model,
            temperature=self.temperature,
            streaming=self.stream,
            openai_api_key=SecretStr(self.auth_token).get_secret_value(),
            base_url=self.base_url,
            model_kwargs={"tool_choice": "none"},
        )
