from __future__ import annotations

import base64
import os
from typing import Any

import requests

from lfx.custom import Component
from lfx.io import (
    DropdownInput,
    FileInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
    TabInput,
)
from lfx.schema import Data
from lfx.schema.message import Message


class ModelImageAnalyzer(Component):
    display_name = "Image Analyzer"
    description = "Analyzes images using multiple providers with model selection."
    icon = "image"
    name = "ModelImageAnalyzerComponent"
    beta=True

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "Google",
    ]

    IMAGE_MODELS_BY_PROVIDER = {
        "OpenAI": ["gpt-4o", "gpt-4o-mini"],
        "Google": ["vision-v1"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with image analysis capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
            options_metadata=[{"icon": "OpenAI"}, {"icon": "GoogleGenerativeAI"}],
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the model.",
            options=[*IMAGE_MODELS_BY_PROVIDER["OpenAI"]],
            value="gpt-4o-mini",
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
            info="Custom API base URL (default: OpenAI). Override to use another compatible endpoint.",
            value="https://api.openai.com/v1",
            advanced=True,
            show=False,
        ),
        TabInput(
            name="image_source",
            display_name="Image Source",
            options=["File", "URL"],
            value="File",
            info="Load image from uploaded file or from a URL.",
            real_time_refresh=True,
        ),
        FileInput(
            name="image_file",
            display_name="File",
            file_types=["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"],
            info="Upload an image file for analysis.",
            required=False,
            show=True,
        ),
        StrInput(
            name="image_url",
            display_name="URL",
            info="URL of the image to analyze.",
            required=False,
            show=False,
        ),
        MessageTextInput(
            name="prompt",
            display_name="Prompt",
            info="Instruction for analysis (OpenAI-compatible only).",
            advanced=True,
        ),
        DropdownInput(
            name="analysis_type",
            display_name="Analysis Type",
            info="Type of analysis for Google Vision.",
            options=[
                "LABEL_DETECTION",
                "TEXT_DETECTION",
                "DOCUMENT_TEXT_DETECTION",
                "FACE_DETECTION",
                "LANDMARK_DETECTION",
                "LOGO_DETECTION",
                "OBJECT_LOCALIZATION",
                "SAFE_SEARCH_DETECTION",
                "IMAGE_PROPERTIES",
                "WEB_DETECTION",
            ],
            value="LABEL_DETECTION",
            show=False,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of results to return for applicable features.",
            value=10,
            show=False,
            advanced=True,
        ),
        StrInput(
            name="language_hints",
            display_name="Language Hints",
            info="Language hints for text detection (comma-separated, e.g., en,pt,es).",
            value="",
            show=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="analysis_data",
            display_name="Analysis Data",
            method="analyze_image",
        ),
        Output(
            name="analysis_text",
            display_name="Analysis Text",
            method="get_analysis_text",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.IMAGE_MODELS_BY_PROVIDER.get(provider, ["gpt-4o-mini"])

            if "model" in build_config:
                build_config["model"]["options"] = model_options
                current_value = build_config["model"].get("value")
                if current_value not in model_options:
                    build_config["model"]["value"] = model_options[0]

            if "base_url" in build_config:
                build_config["base_url"]["value"] = self.BASE_URL_BY_PROVIDER.get(
                    provider, "https://api.openai.com/v1"
                )
                build_config["base_url"]["show"] = provider == "OpenAI"

            google_visible = provider == "Google"
            for field in ("analysis_type", "max_results", "language_hints"):
                if field in build_config:
                    build_config[field]["show"] = google_visible

        elif field_name == "image_source":
            source = field_value or build_config.get("image_source", {}).get("value") or "File"
            if "image_file" in build_config:
                build_config["image_file"]["show"] = source == "File"
            if "image_url" in build_config:
                build_config["image_url"]["show"] = source == "URL"

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "gpt-4o-mini"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_openai_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _get_image_source(self) -> tuple[str | None, str | None]:
        source = getattr(self, "image_source", "File") or "File"

        if source == "File":
            if not self.image_file:
                return None, "Image file is required."
            image_path = self.image_file
            if isinstance(image_path, list):
                image_path = image_path[0] if image_path else None
            if not image_path or not os.path.exists(image_path):
                return None, f"Image file not found at {image_path}"
            if os.path.getsize(image_path) == 0:
                return None, "Image file is empty."
            return image_path, None

        if source == "URL":
            if not self.image_url or not str(self.image_url).strip():
                return None, "Image URL is required."
            return str(self.image_url).strip(), None

        return None, "Image file or image URL is required."

    def _get_api_key(self) -> tuple[str | None, str | None]:
        if not self.api_key:
            return None, "API key is required."

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()
        if not api_key:
            return None, "A valid API key is required."

        return api_key, None

    def _build_openai_image_url(self, image_source: str) -> str:
        if image_source.startswith("http"):
            return image_source

        with open(image_source, "rb") as f:
            image_data = f.read()

        base64_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_image}"

    def _analyze_openai(self, api_key: str, image_source: str, model: str, prompt: str) -> dict:
        url = self._build_openai_url(getattr(self, "base_url", "https://api.openai.com/v1"))
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        prompt_text = prompt.strip() if prompt else "Describe the image or extract text if present."
        image_url = self._build_openai_image_url(image_source)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "max_tokens": 1024,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                return {"error": "OpenAI response missing content."}
            return {"text": text, "provider": "OpenAI", "model": model}

        return {"error": f"API Error {response.status_code}: {response.text}"}

    def _build_google_payload(self, image_source: str) -> dict[str, Any]:
        if image_source.startswith("http"):
            image_content = {"source": {"imageUri": image_source}}
        else:
            with open(image_source, "rb") as f:
                image_content = {"content": base64.b64encode(f.read()).decode("utf-8")}

        feature = {"type": self.analysis_type}
        if self.analysis_type in [
            "LABEL_DETECTION",
            "FACE_DETECTION",
            "LANDMARK_DETECTION",
            "LOGO_DETECTION",
            "OBJECT_LOCALIZATION",
            "WEB_DETECTION",
        ]:
            feature["maxResults"] = self.max_results

        payload: dict[str, Any] = {
            "requests": [{"image": image_content, "features": [feature]}]
        }

        if self.language_hints and self.analysis_type in ("TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION"):
            language_list = [lang.strip() for lang in self.language_hints.split(",") if lang.strip()]
            if language_list:
                payload["requests"][0]["imageContext"] = {"languageHints": language_list}

        return payload

    def _extract_google_text(self, response_data: dict) -> str | None:
        responses = response_data.get("responses") or []
        if not responses:
            return None

        response = responses[0]
        if "fullTextAnnotation" in response:
            return response["fullTextAnnotation"].get("text")

        if "textAnnotations" in response and response["textAnnotations"]:
            return response["textAnnotations"][0].get("description")

        if "labelAnnotations" in response:
            labels = [label.get("description") for label in response["labelAnnotations"] if label.get("description")]
            if labels:
                return ", ".join(labels)

        return None

    def _analyze_google(self, api_key: str, image_source: str) -> dict:
        endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        payload = self._build_google_payload(image_source)
        headers = {"Content-Type": "application/json"}

        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            text = self._extract_google_text(data)
            if text:
                return {
                    "text": text,
                    "provider": "Google",
                    "model": getattr(self, "model", "vision-v1"),
                    "analysis_type": self.analysis_type,
                    "raw_response": data,
                }
            return {
                "provider": "Google",
                "model": getattr(self, "model", "vision-v1"),
                "analysis_type": self.analysis_type,
                "raw_response": data,
            }

        return {"error": f"API Error {response.status_code}: {response.text}"}

    def _analyze_internal(self) -> dict:
        image_source, image_error = self._get_image_source()
        if image_error:
            return {"error": image_error}

        api_key, api_error = self._get_api_key()
        if api_error:
            return {"error": api_error}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        model = self._normalize_model(getattr(self, "model", "gpt-4o-mini"))
        prompt = getattr(self, "prompt", "") or ""

        if provider == "OpenAI":
            return self._analyze_openai(api_key, image_source, model, prompt)

        if provider == "Google":
            return self._analyze_google(api_key, image_source)

        return {"error": f"Unsupported provider: {provider}"}

    def analyze_image(self) -> Data:
        result = self._analyze_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        return Data(data=result)

    def get_analysis_text(self) -> Message:
        result = self._analyze_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result.get("text", ""))
