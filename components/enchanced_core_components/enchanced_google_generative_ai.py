from typing import Any

import requests
from pydantic.v1 import SecretStr

from langflow.base.models.google_generative_ai_constants import GOOGLE_GENERATIVE_AI_MODELS
from langflow.base.models.model import LCModelComponent
from langflow.field_typing import LanguageModel
from langflow.field_typing.range_spec import RangeSpec
from langflow.inputs.inputs import BoolInput, DropdownInput, FloatInput, IntInput, SecretStrInput, SliderInput, StrInput, DictInput
from langflow.logging.logger import logger
from langflow.schema.dotdict import dotdict


class GoogleGenerativeAIComponent(LCModelComponent):
    display_name = "Google Generative AI"
    description = "Generate text using Google Generative AI."
    icon = "GoogleGenerativeAI"
    name = "GoogleGenerativeAIModel"

    inputs = [
        *LCModelComponent._base_inputs,
        IntInput(
            name="max_output_tokens", display_name="Max Output Tokens", info="The maximum number of tokens to generate."
        ),
        DropdownInput(
            name="model_name",
            display_name="Model",
            info="The name of the model to use.",
            options=GOOGLE_GENERATIVE_AI_MODELS,
            value="gemini-2.0-flash-exp",
            refresh_button=True,
            combobox=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="Google API Key",
            info="The Google API Key to use for the Google Generative AI.",
            required=True,
            real_time_refresh=True,
        ),
        FloatInput(
            name="top_p",
            display_name="Top P",
            info="The maximum cumulative probability of tokens to consider when sampling.",
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name="Temperature",
            value=0.1,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            info="Controls randomness. Lower values are more deterministic, higher values are more creative.",
        ),
        IntInput(
            name="n",
            display_name="N",
            info="Number of chat completions to generate for each prompt. "
            "Note that the API may not return the full n completions if duplicates are generated.",
            advanced=True,
        ),
        IntInput(
            name="top_k",
            display_name="Top K",
            info="Decode using top-k sampling: consider the set of top_k most probable tokens. Must be positive.",
            advanced=True,
        ),
        BoolInput(
            name="tool_model_enabled",
            display_name="Tool Model Enabled",
            info="Whether to use the tool model.",
            value=False,
        ),
        StrInput(
            name="system_instruction",
            display_name="System Instruction",
            info="System-level instructions to guide the model's behavior.",
            advanced=True,
        ),
        DictInput(
            name="safety_settings",
            display_name="Safety Settings",
            info="Dictionary of safety settings to control content filtering. "
            "Example: {'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_MEDIUM_AND_ABOVE'}",
            advanced=True,
        ),
        DropdownInput(
            name="response_mime_type",
            display_name="Response MIME Type",
            info="The MIME type of the response. Select 'application/json' for structured output. "
            "Note: Structured output only works with Gemini 2.0+ models (gemini-2.0-flash-exp, gemini-2.5-pro, etc.)",
            options=["text/plain", "application/json"],
            value="text/plain",
            advanced=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="output_type",
            display_name="Output Type",
            info="Select the type of structured output.",
            options=["object", "array"],
            value="object",
            advanced=True,
            show=False,
        ),
        StrInput(
            name="output_field_name",
            display_name="Output Field Name",
            info="Name of the output field (e.g., 'response', 'answer', 'result').",
            value="response",
            advanced=True,
            show=False,
        ),
        DropdownInput(
            name="output_field_type",
            display_name="Output Field Type",
            info="Data type of the output field.",
            options=["string", "number", "boolean", "array"],
            value="string",
            advanced=True,
            show=False,
        ),
        IntInput(
            name="candidate_count",
            display_name="Candidate Count",
            info="Number of response candidates to generate. Alternative to 'N' parameter.",
            value=1,
            advanced=True,
        ),
        StrInput(
            name="stop_sequences",
            display_name="Stop Sequences",
            info="Comma-separated list of sequences where the model will stop generating tokens.",
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            msg = "The 'langchain_google_genai' package is required to use the Google Generative AI model."
            raise ImportError(msg) from e

        google_api_key = self.api_key
        model = self.model_name
        max_output_tokens = self.max_output_tokens
        temperature = self.temperature
        top_k = self.top_k
        top_p = self.top_p
        n = self.n
        system_instruction = self.system_instruction
        safety_settings = self.safety_settings
        response_mime_type = self.response_mime_type
        candidate_count = self.candidate_count
        stop_sequences = self.stop_sequences
        output_type = self.output_type
        output_field_name = self.output_field_name
        output_field_type = self.output_field_type

        # Prepare stop sequences as a list if provided
        stop_sequences_list = None
        if stop_sequences:
            stop_sequences_list = [seq.strip() for seq in stop_sequences.split(",") if seq.strip()]

        # Build the model with all parameters
        model_params = {
            "model": model,
            "max_output_tokens": max_output_tokens or None,
            "temperature": temperature,
            "top_k": top_k or None,
            "top_p": top_p or None,
            "n": n or 1,
            "google_api_key": SecretStr(google_api_key).get_secret_value(),
        }

        # Add optional parameters if they are provided
        # Note: system_instruction is handled in the JSON schema section if JSON is selected
        if system_instruction and response_mime_type != "application/json":
            model_params["system_instruction"] = system_instruction
        
        if safety_settings:
            model_params["safety_settings"] = safety_settings
        
        # Handle structured output when JSON is selected
        if response_mime_type == "application/json":
            # Check if model supports structured output
            supported_models = ["gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"]
            if any(supported_model in model for supported_model in supported_models):
                # Automatically build schema based on user selections
                if output_type == "object":
                    response_schema = {
                        "type": "object",
                        "properties": {
                            output_field_name: {"type": output_field_type}
                        },
                        "required": [output_field_name]
                    }
                elif output_type == "array":
                    response_schema = {
                        "type": "array",
                        "items": {"type": output_field_type}
                    }
                
                logger.info(f"Model: {model} - Auto-generated response_schema: {response_schema}")
                
                # Try different parameter approaches for langchain-google-genai
                
                # Approach 1: Direct parameters
                model_params["response_mime_type"] = "application/json"
                model_params["response_schema"] = response_schema
                
                # Approach 2: Using generation_config (Google AI Studio style)
                generation_config = {
                    "response_mime_type": "application/json",
                    "response_schema": response_schema
                }
                model_params["generation_config"] = generation_config
                
                # Approach 3: Using model_kwargs (langchain fallback)
                model_kwargs = {
                    "response_mime_type": "application/json", 
                    "response_schema": response_schema,
                    "generation_config": generation_config
                }
                model_params["model_kwargs"] = model_kwargs
                
                # Add schema enforcement to system instruction as backup
                schema_instruction = f"You must respond with valid JSON that strictly follows this schema: {response_schema}. " \
                                   f"The response must contain the field '{output_field_name}' of type '{output_field_type}'. " \
                                   f"Do not include any text outside the JSON structure."
                
                if system_instruction:
                    model_params["system_instruction"] = f"{system_instruction}\n\n{schema_instruction}"
                else:
                    model_params["system_instruction"] = schema_instruction
                
                # Debug: print all parameters being passed
                logger.info(f"Schema being enforced: {response_schema}")
                logger.info(f"Field name expected: {output_field_name}")
                logger.info(f"Enhanced system instruction: {model_params.get('system_instruction')}")
            else:
                logger.warning(f"Model {model} may not support structured output. Supported models: {supported_models}")
                model_params["response_mime_type"] = "application/json"
        elif response_mime_type and response_mime_type != "text/plain":
            model_params["response_mime_type"] = response_mime_type
        
        if candidate_count and candidate_count > 1:
            model_params["candidate_count"] = candidate_count
        
        if stop_sequences_list:
            model_params["stop_sequences"] = stop_sequences_list

        return ChatGoogleGenerativeAI(**model_params)

    def get_models(self, *, tool_model_enabled: bool | None = None) -> list[str]:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model_ids = [
                model.name.replace("models/", "")
                for model in genai.list_models()
                if "generateContent" in model.supported_generation_methods
            ]
            model_ids.sort(reverse=True)
        except (ImportError, ValueError) as e:
            logger.exception(f"Error getting model names: {e}")
            model_ids = GOOGLE_GENERATIVE_AI_MODELS
        if tool_model_enabled:
            try:
                from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
            except ImportError as e:
                msg = "langchain_google_genai is not installed."
                raise ImportError(msg) from e
            for model in model_ids:
                model_with_tool = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                )
                if not self.supports_tool_calling(model_with_tool):
                    model_ids.remove(model)
        return model_ids

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name in {"base_url", "model_name", "tool_model_enabled", "api_key"} and field_value:
            try:
                if len(self.api_key) == 0:
                    ids = GOOGLE_GENERATIVE_AI_MODELS
                else:
                    try:
                        ids = self.get_models(tool_model_enabled=self.tool_model_enabled)
                    except (ImportError, ValueError, requests.exceptions.RequestException) as e:
                        logger.exception(f"Error getting model names: {e}")
                        ids = GOOGLE_GENERATIVE_AI_MODELS
                build_config.setdefault("model_name", {})
                build_config["model_name"]["options"] = ids
                build_config["model_name"].setdefault("value", ids[0] if ids else "gemini-2.0-flash-exp")
            except Exception as e:
                msg = f"Error getting model names: {e}"
                raise ValueError(msg) from e
        
        # Handle conditional display of structured output fields
        if field_name == "response_mime_type":
            is_json = field_value == "application/json"
            
            # Show/hide structured output fields based on MIME type selection
            build_config.setdefault("output_type", {})
            build_config["output_type"]["show"] = is_json
            
            build_config.setdefault("output_field_name", {})
            build_config["output_field_name"]["show"] = is_json
            
            build_config.setdefault("output_field_type", {})
            build_config["output_field_type"]["show"] = is_json
            
        return build_config
