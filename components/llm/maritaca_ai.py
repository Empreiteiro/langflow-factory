"""Maritaca AI LLM component.

Uses the Maritaca API (OpenAI-compatible) for chat completions with Sabiá models.
Documentation: https://docs.maritaca.ai/pt/api/openai-compatibilidade
"""

from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput
from lfx.io import DropdownInput, MessageInput, MultilineInput, SecretStrInput, SliderInput

MARITACA_BASE_URL = "https://chat.maritaca.ai/api"

# Modelos Sabiá disponíveis na API Maritaca (documentação: sabia-4)
MARITACA_MODEL_OPTIONS = [
    "sabia-4",
    "sabia-3",
]


class MaritacaAIComponent(LCModelComponent):
    display_name = "Maritaca AI"
    description = (
        "Chat com modelos Sabiá da Maritaca AI. API compatível com OpenAI. "
        "Use sua chave em https://chat.maritaca.ai e escolha o modelo."
    )
    documentation: str = "https://docs.maritaca.ai/pt/api/openai-compatibilidade"
    icon = "message-circle"
    name = "MaritacaAI"
    category = "models"

    inputs = [
        DropdownInput(
            name="model",
            display_name="Model",
            options=MARITACA_MODEL_OPTIONS,
            value=MARITACA_MODEL_OPTIONS[0],
            info="Modelo Sabiá da Maritaca (ex.: sabia-4).",
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="Maritaca API Key",
            info="Chave de API obtida em https://chat.maritaca.ai (MARITACA_API_KEY).",
            required=True,
            real_time_refresh=True,
        ),
        MessageInput(
            name="input_value",
            display_name="Input",
            info="O texto de entrada para o modelo.",
        ),
        MultilineInput(
            name="system_message",
            display_name="System Message",
            info="Mensagem de sistema que define o comportamento do assistente.",
            advanced=False,
        ),
        BoolInput(
            name="stream",
            display_name="Stream",
            info="Se deve retornar a resposta em streaming.",
            value=False,
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name="Temperature",
            value=0.1,
            info="Controla a aleatoriedade das respostas.",
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:
        if not self.api_key:
            raise ValueError("Maritaca API key is required.")

        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            streaming=self.stream,
            openai_api_key=SecretStr(self.api_key).get_secret_value(),
            base_url=MARITACA_BASE_URL,
        )
