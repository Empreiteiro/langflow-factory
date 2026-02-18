"""
Unified video generation component (multi-provider).
Follows the same pattern as core/image_generator.py.
Supports Google Veo and OpenAI (Sora placeholder when API is available).
"""
from __future__ import annotations

import time
from typing import Any

import requests

from lfx.custom import Component
from lfx.io import (
    DropdownInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema import Data
from lfx.schema.message import Message


class ModelVideoGenerator(Component):
    display_name = "Video Generator"
    description = "Generates videos from text prompts using multiple providers."
    icon = "video"
    name = "ModelVideoGeneratorComponent"
    beta = True

    MODEL_PROVIDERS_LIST = [
        "Google",
        "OpenAI",
    ]

    VIDEO_MODELS_BY_PROVIDER = {
        "Google": [
            "veo-3.1-generate-preview",
            "veo-3.0-generate-001",
            "veo-3.0-generate-preview",
            "veo-2.0-generate-001",
        ],
        "OpenAI": ["sora-1"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider for video generation.",
            options=[*MODEL_PROVIDERS_LIST],
            value="Google",
            real_time_refresh=True,
            options_metadata=[{"icon": "GoogleGenerativeAI"}, {"icon": "OpenAI"}],
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the video generation model.",
            options=[*VIDEO_MODELS_BY_PROVIDER["Google"]],
            value="veo-3.0-generate-001",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key (Gemini for Google, OpenAI for Sora).",
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
        MessageTextInput(
            name="prompt",
            display_name="Prompt",
            info="Text prompt describing the video to generate.",
            required=True,
        ),
        DropdownInput(
            name="aspect_ratio",
            display_name="Aspect Ratio",
            info="Video format ratio (Google Veo).",
            options=["16:9", "9:16"],
            value="16:9",
            show=True,
        ),
        DropdownInput(
            name="allow_people",
            display_name="Allow People",
            info="Whether to allow people in generated videos (Google Veo).",
            options=["default", "allow_adult"],
            value="default",
            show=True,
        ),
        DropdownInput(
            name="size",
            display_name="Video Size",
            info="Resolution of the video (OpenAI Sora).",
            options=["1024x1024", "1280x720", "1920x1080"],
            value="1280x720",
            show=False,
        ),
        StrInput(
            name="n_frames",
            display_name="Number of Frames",
            info="Number of frames (OpenAI Sora, e.g. 30, 60, 120).",
            value="30",
            show=False,
        ),
    ]

    outputs = [
        Output(
            name="generated_video",
            display_name="Generated Video",
            method="generate_video",
        ),
        Output(
            name="video_url",
            display_name="Video URL",
            method="get_video_url",
        ),
        Output(
            name="markdown_output",
            display_name="Markdown",
            method="get_markdown",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.VIDEO_MODELS_BY_PROVIDER.get(provider, list(self.VIDEO_MODELS_BY_PROVIDER.values())[0])
            if "model" in build_config:
                build_config["model"]["options"] = model_options
                current = build_config["model"].get("value")
                if current not in model_options:
                    build_config["model"]["value"] = model_options[0]
            if "base_url" in build_config:
                build_config["base_url"]["value"] = self.BASE_URL_BY_PROVIDER.get(
                    provider, "https://api.openai.com/v1"
                )
                build_config["base_url"]["show"] = provider == "OpenAI"

            google_visible = provider == "Google"
            openai_visible = provider == "OpenAI"
            for key in ("aspect_ratio", "allow_people"):
                if key in build_config:
                    build_config[key]["show"] = google_visible
            for key in ("size", "n_frames"):
                if key in build_config:
                    build_config[key]["show"] = openai_visible

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "veo-3.0-generate-001"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _get_prompt_text(self) -> str:
        raw = getattr(self, "prompt", "") or ""
        if hasattr(raw, "text"):
            return (raw.text or "").strip()
        return str(raw).strip()

    def _get_api_key(self) -> tuple[str | None, str | None]:
        if not self.api_key:
            return None, "API key is required."
        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()
        if not api_key:
            return None, "A valid API key is required."
        return api_key, None

    def _generate_veo(self, api_key: str, prompt: str, model: str) -> dict[str, Any]:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return {"error": "Google GenAI SDK is required. Install with: pip install google-genai"}

        aspect_ratio = getattr(self, "aspect_ratio", "16:9") or "16:9"
        allow_people = getattr(self, "allow_people", "default") or "default"

        config_kwargs: dict[str, Any] = {"aspect_ratio": aspect_ratio}
        if allow_people != "default":
            config_kwargs["person_generation"] = allow_people

        client = genai.Client(api_key=api_key)
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_kwargs),
        )

        self.status = f"Waiting for video generation ({model})..."
        while not operation.done:
            time.sleep(20)
            operation = client.operations.get(operation)

        video_urls = []
        for generated_video in operation.response.generated_videos or []:
            if hasattr(generated_video, "video") and generated_video.video and hasattr(generated_video.video, "uri"):
                video_urls.append(f"{generated_video.video.uri}&key={api_key}")

        if not video_urls:
            return {"error": "No video was generated."}

        self.status = f"Video generated with {model}."
        return {
            "video_url": video_urls[0],
            "video_urls": video_urls,
            "provider": "Google",
            "model": model,
            "aspect_ratio": aspect_ratio,
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        }

    def _generate_openai(self, api_key: str, prompt: str, model: str) -> dict[str, Any]:
        base_url = getattr(self, "base_url", "https://api.openai.com/v1") or "https://api.openai.com/v1"
        size = getattr(self, "size", "1280x720") or "1280x720"
        try:
            n_frames = int(getattr(self, "n_frames", "30") or "30")
        except (TypeError, ValueError):
            n_frames = 30

        base = base_url.rstrip("/")
        endpoints = [
            f"{base}/v1/videos/generations" if not base.endswith("/v1") else f"{base}/videos/generations",
            "https://api.openai.com/v1/videos/generations",
        ]
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "prompt": prompt, "size": size, "n_frames": n_frames}

        for url in endpoints:
            try:
                self.log(f"Trying endpoint: {url}")
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("data") or []
                    video_url = items[0].get("url") if items else None
                    if video_url:
                        return {
                            "video_url": video_url,
                            "video_urls": [video_url],
                            "provider": "OpenAI",
                            "model": model,
                            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                        }
                elif response.status_code != 404:
                    self.log(f"Endpoint returned {response.status_code}: {response.text}")
            except Exception as e:
                self.log(f"Error with endpoint: {e}")
                continue

        return {
            "error": (
                "OpenAI video API (Sora) may not be publicly available yet. "
                "Use Google (Veo) provider or check OpenAI documentation for updates."
            ),
        }

    def _generate_internal(self) -> dict[str, Any]:
        prompt_text = self._get_prompt_text()
        if not prompt_text:
            return {"error": "Prompt is required."}

        api_key, api_error = self._get_api_key()
        if api_error:
            return {"error": api_error}

        provider = getattr(self, "provider", "Google") or "Google"
        model = self._normalize_model(getattr(self, "model", "veo-3.0-generate-001"))

        if provider == "Google":
            return self._generate_veo(api_key, prompt_text, model)
        if provider == "OpenAI":
            return self._generate_openai(api_key, prompt_text, model)

        return {"error": f"Unsupported provider: {provider}"}

    def generate_video(self) -> Data:
        result = self._generate_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        return Data(data=result)

    def get_video_url(self) -> Message:
        result = self._generate_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result.get("video_url", ""))

    def get_markdown(self) -> Message:
        result = self._generate_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        url = result.get("video_url", "")
        if not url:
            return Message(text="Error: No video URL.")
        aspect = result.get("aspect_ratio", "16:9") or "16:9"
        width, height = (640, 360) if aspect == "16:9" else (360, 640)
        html = f'<video width="{width}" height="{height}" controls>\n  <source src="{url}">\n</video>'
        return Message(text=html)
