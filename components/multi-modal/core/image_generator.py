from __future__ import annotations

from typing import Any

import requests

from lfx.custom import Component
from lfx.io import (
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema import Data
from lfx.schema.message import Message


class ModelImageGenerator(Component):
    display_name = "Image Generator"
    description = "Generates images from text prompts using multiple providers."
    icon = "image"
    name = "ModelImageGeneratorComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
    ]

    IMAGE_MODELS_BY_PROVIDER = {
        "OpenAI": ["dall-e-3", "dall-e-2"],
        "OpenAI-Compatible": ["dall-e-3", "dall-e-2"],
    }

    SIZE_BY_MODEL = {
        "dall-e-3": ["1024x1024", "1792x1024", "1024x1792"],
        "dall-e-2": ["256x256", "512x512", "1024x1024"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider for image generation.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the image generation model.",
            options=[*IMAGE_MODELS_BY_PROVIDER["OpenAI"]],
            value="dall-e-3",
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
        MessageTextInput(
            name="prompt",
            display_name="Prompt",
            info="Text prompt describing the image to generate.",
            required=True,
        ),
        IntInput(
            name="n",
            display_name="Number of Images",
            info="Number of images to generate (DALL-E 3 supports only 1).",
            value=1,
        ),
        DropdownInput(
            name="size",
            display_name="Image Size",
            info="Size of the generated image.",
            options=["1024x1024", "1792x1024", "1024x1792"],
            value="1024x1024",
        ),
    ]

    outputs = [
        Output(
            name="generated_images",
            display_name="Generated Images",
            method="generate_images",
        ),
        Output(
            name="image_url",
            display_name="Image URL",
            method="get_image_url",
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
            model_options = self.IMAGE_MODELS_BY_PROVIDER.get(provider, ["dall-e-3"])
            if "model" in build_config:
                build_config["model"]["options"] = model_options
                current = build_config["model"].get("value")
                if current not in model_options:
                    build_config["model"]["value"] = model_options[0]
            if "base_url" in build_config:
                build_config["base_url"]["value"] = self.BASE_URL_BY_PROVIDER.get(
                    provider, "https://api.openai.com/v1"
                )
                build_config["base_url"]["show"] = provider == "OpenAI-Compatible"

        if field_name == "model" or field_name == "provider":
            model = field_value if field_name == "model" else build_config.get("model", {}).get("value")
            if not model and field_name == "provider":
                model = build_config.get("model", {}).get("value") or "dall-e-3"
            size_options = self.SIZE_BY_MODEL.get(model, ["1024x1024", "1792x1024", "1024x1792"])
            if "size" in build_config:
                build_config["size"]["options"] = size_options
                if build_config["size"].get("value") not in size_options:
                    build_config["size"]["value"] = size_options[0]
            if model == "dall-e-3" and "n" in build_config:
                build_config["n"]["value"] = 1

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "dall-e-3"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_generations_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/images/generations"
        return f"{base}/v1/images/generations"

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

    def _generate_internal(self) -> dict[str, Any]:
        prompt_text = self._get_prompt_text()
        if not prompt_text:
            return {"error": "Prompt is required."}

        api_key, api_error = self._get_api_key()
        if api_error:
            return {"error": api_error}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        model = self._normalize_model(getattr(self, "model", "dall-e-3"))
        n = getattr(self, "n", 1) or 1
        size = getattr(self, "size", "1024x1024") or "1024x1024"

        if model == "dall-e-3":
            n = 1

        url = self._build_generations_url(getattr(self, "base_url", "https://api.openai.com/v1"))
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt_text,
            "n": int(n),
            "size": size,
        }

        try:
            self.status = f"Generating image(s) with {model}..."
            self.log(f"Requesting images: model={model}, n={n}, size={size}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code != 200:
                return {"error": f"API Error {response.status_code}: {response.text}"}

            data = response.json()
            items = data.get("data") or []
            image_urls = [item.get("url") for item in items if item.get("url")]

            if not image_urls:
                return {"error": "No image URL in response."}

            self.status = f"Generated {len(image_urls)} image(s)."
            return {
                "image_urls": image_urls,
                "image_url": image_urls[0],
                "provider": provider,
                "model": model,
                "size": size,
                "count": len(image_urls),
                "prompt": prompt_text[:200] + "..." if len(prompt_text) > 200 else prompt_text,
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def generate_images(self) -> Data:
        result = self._generate_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        out = {k: v for k, v in result.items() if k != "image_url"}
        if result.get("count") == 1 and result.get("image_urls"):
            out["image_url"] = result["image_urls"][0]
        return Data(data=out)

    def get_image_url(self) -> Message:
        result = self._generate_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result.get("image_url", ""))

    def get_markdown(self) -> Message:
        result = self._generate_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        url = result.get("image_url", "")
        if not url:
            return Message(text="Error: No image URL.")
        prompt = result.get("prompt", "") or "Generated image"
        desc = prompt[:50] + "..." if len(prompt) > 50 else prompt
        return Message(text=f"![{desc}]({url})")
