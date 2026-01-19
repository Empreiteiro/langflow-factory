import json
import re
from typing import Any

import requests
from langflow.base.models.model import LCModelComponent
from langflow.inputs import SecretStrInput
from langflow.io import MessageInput, MessageTextInput, Output
from langflow.schema import Data
from loguru import logger


class NVIDIANeMoGuardrailsComponent(LCModelComponent):
    display_name = "NeMo Content Safety"
    description = (
        "Check content safety with NVIDIA NeMoGuard."
    )
    icon = "NVIDIA"
    name = "NVIDIANemoGuardrails"

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="Text to analyze for content safety.",
            required=True,
        ),
        MessageTextInput(
            name="base_url",
            display_name="NIM Base URL",
            value="https://integrate.api.nvidia.com/v1",
            info="Base URL for NVIDIA NIM APIs",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        SecretStrInput(
            name="auth_token",
            display_name="NIM API Key",
            info="API key for NVIDIA NIM",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        MessageInput(
            name="safe_override",
            display_name="Safe Override",
            info="Optional message to return when content is safe.",
            required=False,
            advanced=True,
        ),
        MessageInput(
            name="unsafe_override",
            display_name="Unsafe Override",
            info="Optional message to return when content is unsafe.",
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Safe", name="safe_result", method="process_safe", group_outputs=True),
        Output(display_name="Unsafe", name="unsafe_result", method="process_unsafe", group_outputs=True),
    ]

    MODEL_NAME = "nvidia/llama-3.1-nemoguard-8b-content-safety"

    def _pre_run_setup(self):
        self._inference_result = None

    def get_auth_headers(self):
        """Get authentication headers for API requests."""
        if not hasattr(self, "auth_token") or not self.auth_token:
            return {
                "accept": "application/json",
                "Content-Type": "application/json",
            }
        return {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }

    def _extract_text_from_json(self, data: Any) -> str | None:
        if isinstance(data, dict):
            for key in ("text", "content"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value
                nested = self._extract_text_from_json(value)
                if nested:
                    return nested
            for value in data.values():
                nested = self._extract_text_from_json(value)
                if nested:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = self._extract_text_from_json(item)
                if nested:
                    return nested
        elif isinstance(data, str) and data.strip():
            return data
        return None

    def _normalize_input(self) -> str:
        input_text = ""
        if hasattr(self, "input_text") and self.input_text:
            input_text = str(self.input_text)

        if input_text:
            try:
                parsed = json.loads(input_text)
                extracted = self._extract_text_from_json(parsed)
                if extracted:
                    input_text = extracted
            except json.JSONDecodeError:
                pass

        return input_text.strip()

    def _find_safety_value(self, data: Any) -> bool | None:
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = str(key).lower()
                if key_lower in ("is_unsafe", "unsafe"):
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, str):
                        if "unsafe" in value.lower():
                            return True
                        if "safe" in value.lower():
                            return False
                if key_lower in ("user safety", "response safety", "safety", "label", "rating", "result"):
                    if isinstance(value, str):
                        if "unsafe" in value.lower():
                            return True
                        if "safe" in value.lower():
                            return False
                nested = self._find_safety_value(value)
                if nested is not None:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = self._find_safety_value(item)
                if nested is not None:
                    return nested
        return None

    def _infer_unsafe_from_text(self, content: str) -> bool | None:
        if not content:
            return None
        unsafe_match = re.search(r"\bunsafe\b", content, re.IGNORECASE)
        safe_match = re.search(r"\bsafe\b", content, re.IGNORECASE)
        if unsafe_match:
            return True
        if safe_match:
            return False
        return None

    def _is_unsafe(self, content: str) -> bool:
        try:
            parsed = json.loads(content)
            parsed_result = self._find_safety_value(parsed)
            if parsed_result is not None:
                return parsed_result
        except json.JSONDecodeError:
            pass

        text_result = self._infer_unsafe_from_text(content)
        if text_result is not None:
            return text_result

        logger.warning("Could not determine safety from response. Defaulting to unsafe.")
        return True

    def _resolve_override(self, override_value: Any) -> str | None:
        if override_value and hasattr(override_value, "text"):
            override_text = str(override_value.text).strip()
            if override_text:
                return override_text
        if isinstance(override_value, str) and override_value.strip():
            return override_value.strip()
        return None

    async def _run_inference(self) -> tuple[bool, str, Any, str]:
        if getattr(self, "_inference_result", None) is not None:
            return self._inference_result

        logger.info("Starting content safety inference")

        input_text = self._normalize_input()
        if not input_text:
            error_message = "The message you want to validate is empty."
            logger.error("Empty input text provided")
            raise ValueError(error_message)

        messages = []
        if hasattr(self, "system_message") and self.system_message:
            messages.append({"role": "system", "content": str(self.system_message)})
        messages.append({"role": "user", "content": input_text})

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {"model": self.MODEL_NAME, "messages": messages}

        try:
            response = requests.post(url, headers=self.get_auth_headers(), json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Error calling NIM endpoint: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
                error_detail = e.response.text
            else:
                error_detail = str(e)
            raise ValueError(f"NIM request failed: {error_detail}") from e

        logger.debug(f"NIM response: {data}")
        content = ""
        try:
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
        except AttributeError:
            content = ""

        if not content:
            content = json.dumps(data, ensure_ascii=True)

        is_unsafe = self._is_unsafe(content)
        self.status = "Unsafe content detected" if is_unsafe else "Content is safe"
        self._inference_result = (is_unsafe, input_text, data, content)
        return self._inference_result

    async def process_safe(self) -> Data:
        is_unsafe, input_text, data, content = await self._run_inference()
        if not is_unsafe:
            self.stop("unsafe_result")
            override = self._resolve_override(getattr(self, "safe_override", None))
            payload = {"text": override or input_text}
            return Data(data=payload)

        self.stop("safe_result")
        return Data(data={})

    async def process_unsafe(self) -> Data:
        is_unsafe, input_text, data, content = await self._run_inference()
        if is_unsafe:
            self.stop("safe_result")
            override = self._resolve_override(getattr(self, "unsafe_override", None))
            reason: Any = content
            try:
                reason = json.loads(content)
            except json.JSONDecodeError:
                reason = content
            payload = {"text": override or input_text, "reason": reason}
            return Data(data=payload)

        self.stop("unsafe_result")
        return Data(data={})
