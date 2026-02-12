from __future__ import annotations

import mimetypes
import os
from typing import Any

import requests

from lfx.custom import Component
from lfx.io import DropdownInput, FileInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema import Data
from lfx.schema.message import Message


class ModelSTT(Component):
    display_name = "STT"
    description = "Converts speech to text using multiple STT providers with model selection."
    icon = "notebook-pen"
    name = "ModelSTTComponent"
    beta=True

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
        "Deepgram",
        "ElevenLabs",
    ]

    STT_MODELS_BY_PROVIDER = {
        "OpenAI": ["whisper-1"],
        "OpenAI-Compatible": ["whisper-1"],
        "Deepgram": ["nova-2", "nova-2-general"],
        "ElevenLabs": ["scribe_v2", "scribe_v1"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with speech-to-text capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the STT model.",
            options=[*STT_MODELS_BY_PROVIDER["OpenAI"]],
            value="whisper-1",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        StrInput(
            name="base_url",
            display_name="API Base URL",
            info="OpenAI-compatible base URL (e.g. https://api.openai.com/v1)",
            value="https://api.openai.com/v1",
            advanced=True,
            show=False,
        ),
        FileInput(
            name="audio_file",
            display_name="File",
            info="Upload an audio file (mp3, mp4, mpeg, mpga, wav, or webm).",
            file_types=["mp3", "mp4", "mpeg", "mpga", "wav", "webm"],
            required=True,
        ),
        StrInput(
            name="language",
            display_name="Language",
            info="Language hint for transcription (e.g. en, pt, pt-BR).",
            advanced=True,
        ),
        MessageTextInput(
            name="prompt",
            display_name="Prompt",
            info="Optional prompt to guide transcription (OpenAI-compatible only).",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="transcription",
            display_name="Transcription",
            method="transcribe_audio",
        ),
        Output(
            name="transcription_text",
            display_name="Transcription Text",
            method="get_transcription_text",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.STT_MODELS_BY_PROVIDER.get(provider, ["whisper-1"])

            if "model" in build_config:
                build_config["model"]["options"] = model_options
                current_value = build_config["model"].get("value")
                if current_value not in model_options:
                    build_config["model"]["value"] = model_options[0]

            if "base_url" in build_config:
                build_config["base_url"]["value"] = self.BASE_URL_BY_PROVIDER.get(
                    provider, "https://api.openai.com/v1"
                )
                build_config["base_url"]["show"] = provider == "OpenAI-Compatible"

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "whisper-1"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_openai_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/audio/transcriptions"
        return f"{base}/v1/audio/transcriptions"

    def _get_audio_path(self) -> tuple[str | None, str | None]:
        if not self.audio_file:
            return None, "Audio file is required."

        audio_path = self.audio_file
        if isinstance(audio_path, list):
            audio_path = audio_path[0] if audio_path else None

        if not audio_path or not os.path.exists(audio_path):
            return None, f"Audio file not found at {audio_path}"

        if os.path.getsize(audio_path) == 0:
            return None, "Audio file is empty."

        return audio_path, None

    def _get_api_key(self) -> tuple[str | None, str | None]:
        if not self.api_key:
            return None, "API key is required."

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()
        if not api_key:
            return None, "A valid API key is required."

        return api_key, None

    def _get_mime_type(self, audio_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(audio_path)
        return mime_type or "application/octet-stream"

    def _transcribe_openai(self, api_key: str, audio_path: str, model: str, language: str, prompt: str) -> dict:
        url = self._build_openai_url(getattr(self, "base_url", "https://api.openai.com/v1"))
        headers = {"Authorization": f"Bearer {api_key}"}

        data: dict[str, Any] = {"model": model}
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt

        file_name = os.path.basename(audio_path)
        content_type = self._get_mime_type(audio_path)

        with open(audio_path, "rb") as audio_file:
            files = {"file": (file_name, audio_file, content_type)}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=60)

        if response.status_code == 200:
            payload = response.json()
            text = payload.get("text")
            if not text:
                return {"error": "Transcription response missing text."}
            return {"text": text, "provider": "OpenAI", "model": model}

        return {"error": f"API Error {response.status_code}: {response.text}"}

    def _transcribe_deepgram(self, api_key: str, audio_path: str, model: str) -> dict:
        url = f"https://api.deepgram.com/v1/listen?model={model}&smart_format=true"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": self._get_mime_type(audio_path),
        }

        with open(audio_path, "rb") as audio_file:
            response = requests.post(url, headers=headers, data=audio_file, timeout=60)

        if response.status_code == 200:
            payload = response.json()
            try:
                text = payload["results"]["channels"][0]["alternatives"][0]["transcript"]
            except (KeyError, IndexError, TypeError):
                return {"error": "Deepgram response missing transcript."}

            if not text:
                return {"error": "Deepgram returned empty transcript."}

            return {"text": text, "provider": "Deepgram", "model": model}

        return {"error": f"API Error {response.status_code}: {response.text}"}

    def _transcribe_elevenlabs(self, api_key: str, audio_path: str, model: str, language: str) -> dict:
        url = "https://api.elevenlabs.io/v1/speech-to-text"
        headers = {"xi-api-key": api_key}

        data: dict[str, Any] = {"model_id": model}
        if language:
            data["language_code"] = language

        file_name = os.path.basename(audio_path)
        content_type = self._get_mime_type(audio_path)

        with open(audio_path, "rb") as audio_file:
            files = {"file": (file_name, audio_file, content_type)}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=60)

        if response.status_code == 200:
            payload = response.json()
            text = payload.get("text")
            if not text:
                return {"error": "Transcription response missing text."}
            return {"text": text, "provider": "ElevenLabs", "model": model}

        return {"error": f"API Error {response.status_code}: {response.text}"}

    def _transcribe_internal(self) -> dict:
        audio_path, audio_error = self._get_audio_path()
        if audio_error:
            return {"error": audio_error}

        api_key, api_error = self._get_api_key()
        if api_error:
            return {"error": api_error}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        model = self._normalize_model(getattr(self, "model", "whisper-1"))
        language = getattr(self, "language", "") or ""
        prompt = getattr(self, "prompt", "") or ""

        if provider in ("OpenAI", "OpenAI-Compatible"):
            return self._transcribe_openai(api_key, audio_path, model, language, prompt)

        if provider == "Deepgram":
            return self._transcribe_deepgram(api_key, audio_path, model)

        if provider == "ElevenLabs":
            return self._transcribe_elevenlabs(api_key, audio_path, model, language)

        return {"error": f"Unsupported provider: {provider}"}

    def transcribe_audio(self) -> Data:
        result = self._transcribe_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        return Data(data=result)

    def get_transcription_text(self) -> Message:
        result = self._transcribe_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result["text"])
