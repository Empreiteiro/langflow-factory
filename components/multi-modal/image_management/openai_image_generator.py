import base64
import json
import struct
import time

import httpx
from openai import OpenAI
from pydantic import SecretStr

from lfx.custom import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import DropdownInput, FileInput, IntInput, MessageInput, Output, SecretStrInput, StrInput
from lfx.schema import Data
from lfx.schema.message import Message


class OpenAIImagesComponent(Component):
    """
    Image generation via OpenAI API.
    Input — prompt. Files — image reference samples for editing (optional).
    """
    display_name = "OpenAI Images"
    description = "Generates images using OpenAI LLMs."
    icon = "OpenAI"
    name = "OpenAIImages"
    version = "0.1.0"

    # Extension -> MIME type
    _EXT_MIME = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "webp": "image/webp",
    }
    # API config
    _DEFAULT_API_BASE = "https://api.openai.com/v1"
    # Model-specific sizes. Same index = same orientation (square, landscape, portrait).
    _VALID_GPT_SIZES = ("1024x1024", "1536x1024", "1024x1536", "auto")
    _VALID_DALLE_SIZES = ("1024x1024", "1792x1024", "1024x1792")
    _ORIENTATION_INDEX = {"square": 0, "landscape": 1, "portrait": 2}
    _GPT_QUALITY_OPTIONS = ("auto", "high", "medium", "low")
    # Retries
    _MAX_RETRIES = 3
    _INITIAL_BACKOFF = 2.0
    _REQUEST_TIMEOUT = 300.0

    inputs = [
        # Core
        MessageInput(
            name="input_value",
            display_name="Input",
            info="Prompt text.",
            required=True,
        ),
        FileInput(
            name="files",
            display_name="Files",
            info="Image reference files (png, jpeg). GPT Image only.",
            file_types=["png", "jpg", "jpeg"],
            is_list=True,
        ),
        # Model & auth
        DropdownInput(
            name="model",
            display_name="Model Name",
            value="gpt-image-1.5",
            options=["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "dall-e-3"],
            info="GPT Image 1.5 — recommended model.",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="OpenAI API Key",
            value="OPENAI_API_KEY",
            required=True,
        ),
        StrInput(
            name="openai_api_base",
            display_name="OpenAI API Base",
            advanced=True,
            info="The base URL of the OpenAI API. "
            "Defaults to https://api.openai.com/v1. "
            "You can change this to use other APIs.",
        ),
        # Image params
        DropdownInput(
            name="orientation",
            display_name="Orientation",
            value="Square",
            options=["Square", "Landscape", "Portrait"],
            info="Mapped to model-specific sizes: GPT Image and DALL-E 3.",
        ),
        DropdownInput(
            name="quality",
            display_name="Quality",
            value="auto",
            options=["auto", "high", "medium", "low"],
            info="Auto — model default, high — best detail, medium/low — faster.",
            advanced=True,
        ),
        DropdownInput(
            name="output_format",
            display_name="Output Format",
            value="png",
            options=["png", "jpeg", "webp"],
            info="GPT Image only.",
            advanced=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="background",
            display_name="Background",
            value="auto",
            options=["auto", "transparent", "opaque"],
            info="Transparency for background. GPT Image only. Auto = model chooses. Transparent requires png or webp.",
            advanced=True,
            real_time_refresh=True,
        ),
        IntInput(
            name="output_compression",
            display_name="Output Compression",
            value=100,
            range_spec=RangeSpec(min=0, max=100),
            info="Compression level 0-100%. GPT Image with webp/jpeg only.",
            advanced=True,
            real_time_refresh=True,
        ),
    ]
    outputs = [
        Output(name="message", display_name="Message", method="get_image_message"),
        Output(name="generated_image", display_name="Generated Image", method="get_generated_image"),
    ]

    def update_build_config(
        self,
        build_config: dict,
        field_value: str,
        field_name: str | None = None,
    ) -> dict:
        """Show/hide GPT-specific fields based on model and output_format."""
        if field_name == "model":
            model = (field_value or "").strip()
            is_gpt = model.startswith("gpt-image")
            for key in ("files", "output_format", "background", "output_compression"):
                if key in build_config:
                    build_config[key]["show"] = is_gpt
            if is_gpt:
                self._apply_output_format_visibility(build_config)
        elif field_name == "output_format":
            if self._is_gpt_model():
                self._apply_output_format_visibility(build_config, output_fmt=field_value)
        return build_config

    def _apply_output_format_visibility(
        self, build_config: dict, output_fmt: str | None = None
    ) -> None:
        """Set visibility of output_compression and background based on output_format."""
        fmt = (output_fmt or getattr(self, "output_format", "png") or "png").strip().lower()
        if "output_compression" in build_config:
            build_config["output_compression"]["show"] = fmt in ("jpeg", "webp")
        if "background" in build_config:
            build_config["background"]["show"] = fmt in ("png", "webp")

    # --- Input helpers ---

    def _file_path_to_data_url(self, file_path: str) -> tuple[str | None, str | None]:
        """
        Reads file by path and returns (data_url, error_message).
        On success: (data:image/...;base64,..., None).
        On error: (None, error_description).
        """
        if not file_path:
            return None, "Empty path"
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "png"
            mime = self._EXT_MIME.get(ext, "image/png")
            b64 = base64.b64encode(content).decode("ascii")
            return f"data:{mime};base64,{b64}", None
        except Exception as e:
            return None, str(e)

    def _get_prompt_text(self) -> str:
        """Extract prompt text from input_value."""
        if self.input_value is None:
            return ""
        return getattr(self.input_value, "text", str(self.input_value)) or ""

    def _get_api_key(self) -> str:
        """Extract API key as plain string."""
        key = self.api_key
        if isinstance(key, SecretStr):
            return key.get_secret_value()
        return key or ""

    def _get_api_base(self) -> str:
        """Returns API base URL, default https://api.openai.com/v1."""
        base = getattr(self, "openai_api_base", None) or ""
        base = (base or "").strip()
        return base if base else self._DEFAULT_API_BASE

    def _is_gpt_model(self) -> bool:
        """Check if current model is GPT Image."""
        model = getattr(self, "model", "") or ""
        return str(model).startswith("gpt-image")

    def _get_resolved_file_paths(self) -> list[str]:
        """Returns resolved file paths for the 'files' input using resolve_path()."""
        raw = getattr(self, "files", None)
        items = raw if isinstance(raw, list) else ([raw] if raw else [])
        paths = []
        for item in items:
            if not item:
                continue
            path = (
                item
                if isinstance(item, str)
                else getattr(item, "path", None) or getattr(item, "file_path", None)
            )
            if path and (resolved := self.resolve_path(path)):
                paths.append(str(resolved))
        return paths

    # --- Validation ---

    def validate_inputs(self) -> None:
        """Validates required inputs before processing."""
        if not self._get_api_key():
            raise ValueError("API Key is not set")

        if not self._get_prompt_text().strip():
            raise ValueError("Enter prompt text in Input")

        model = getattr(self, "model", None) or ""
        if not str(model).strip():
            raise ValueError("Model is not selected")

    # --- Request building ---

    def _get_size(self) -> str:
        """Returns valid size for current model based on orientation."""
        orientation = str(getattr(self, "orientation", "Square")).strip().lower()
        index = self._ORIENTATION_INDEX.get(orientation, 0)
        sizes = self._VALID_GPT_SIZES if self._is_gpt_model() else self._VALID_DALLE_SIZES
        return sizes[index]

    def _parse_size(self, size: str) -> tuple[int | None, int | None]:
        """Parses size string 'WxH' to (width, height). Returns (None, None) for 'auto'."""
        if not size or size == "auto":
            return None, None
        parts = size.split("x")
        if len(parts) != 2:
            return None, None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None

    def _get_image_dimensions(self, b64: str, fmt: str) -> tuple[int | None, int | None]:
        """Reads width/height from image bytes. Supports PNG and JPEG."""
        try:
            raw = base64.b64decode(b64, validate=True)
        except Exception:
            return None, None
        if fmt == "png" and raw[:8] == b"\x89PNG\r\n\x1a\n":
            if len(raw) >= 24:
                w, h = struct.unpack(">II", raw[16:24])
                return w, h
        if fmt in ("jpeg", "jpg") and raw[:2] == b"\xff\xd8":
            i = 2
            while i < len(raw) - 1:
                if raw[i] != 0xFF:
                    i += 1
                    continue
                marker = raw[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    if i + 9 <= len(raw):
                        h, w = struct.unpack(">HH", raw[i + 5 : i + 9])
                        return w, h
                if marker in (0xD8, 0xD9, 0x01):
                    i += 2
                    continue
                if i + 4 <= len(raw):
                    size = struct.unpack(">H", raw[i + 2 : i + 4])[0]
                    i += 2 + size
                else:
                    break
        return None, None

    def _get_quality_and_format(self, model: str) -> dict:
        """Returns quality, output_format, background, output_compression for model."""
        model = (model or "").strip()
        if model.startswith("gpt-image"):
            output_fmt = getattr(self, "output_format", "png") or "png"
            result = {
                "quality": self.quality if self.quality in self._GPT_QUALITY_OPTIONS else "auto",
                "output_format": output_fmt,
                "background": getattr(self, "background", "auto") or "auto",
            }
            if output_fmt in ("webp", "jpeg"):
                comp = getattr(self, "output_compression", 100)
                result["output_compression"] = max(0, min(100, int(comp) if comp is not None else 100))
            return result
        # DALL-E 3: translate unified quality to standard/hd, always b64_json
        result = {"response_format": "b64_json"}
        result["quality"] = "hd" if self.quality == "high" else "standard"
        return result

    def _build_edit_body(
        self,
        prompt: str,
        image_refs: list[dict],
        size: str,
    ) -> dict:
        """Builds request body for images.edit."""
        edit_model = (getattr(self, "model", None) or "gpt-image-1.5") if self._is_gpt_model() else "gpt-image-1.5"
        edit_size = size if size in self._VALID_GPT_SIZES else "1024x1024"
        body = {
            "model": edit_model,
            "prompt": prompt,
            "images": image_refs,
            "size": edit_size,
            "n": 1,
        }
        body.update(self._get_quality_and_format(edit_model))
        return body

    def _build_generate_kwargs(self, prompt: str, size: str) -> dict:
        """Builds kwargs for client.images.generate."""
        model = getattr(self, "model", None) or "gpt-image-1.5"
        kwargs = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        }
        kwargs.update(self._get_quality_and_format(model))
        return kwargs

    # --- API ---

    def _parse_api_error(self, response: httpx.Response) -> str:
        """Extract error message from API response."""
        try:
            data = response.json()
            if "error" in data:
                return data.get("error", {}).get("message", response.text)
        except Exception:
            pass
        return response.text

    def _post_with_retry(
        self,
        url: str,
        headers: dict,
        json_body: dict,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Performs POST with exponential backoff on 429."""
        if timeout is None:
            timeout = self._REQUEST_TIMEOUT
        backoff = self._INITIAL_BACKOFF
        for attempt in range(self._MAX_RETRIES):
            response = httpx.post(url, headers=headers, json=json_body, timeout=timeout)
            if response.status_code != 429:
                return response
            if attempt < self._MAX_RETRIES - 1:
                self.log(f"Rate limit (429), retry {attempt + 1}/{self._MAX_RETRIES} in {backoff:.1f}s")
                time.sleep(backoff)
                backoff *= 2
        return response

    def _run_edit_flow(
        self,
        prompt: str,
        file_paths: list[str],
        api_key: str,
        api_base: str,
        size: str,
    ) -> dict | Message:
        """Run edit flow via images/edits endpoint. Returns image dict or error Message."""
        image_refs = []
        for path in file_paths:
            data_url, err = self._file_path_to_data_url(path)
            if data_url:
                image_refs.append({"image_url": data_url})
            else:
                self.log(f"Failed to read file {path}: {err}")

        if not image_refs:
            return Message(text="Failed to read any image file", category="error")

        body = self._build_edit_body(prompt, image_refs, size)
        edit_url = f"{api_base.rstrip('/')}/images/edits"
        log_body = {**body, "images": [f"<base64, {len(ir['image_url'])} chars>" for ir in body["images"]]}
        self.log(
            f"OpenAI images.edit: POST {edit_url}\n"
            f"Body: {json.dumps(log_body, ensure_ascii=False, indent=2)}"
        )
        response = self._post_with_retry(
            edit_url,
            headers={"Authorization": f"Bearer {api_key}"},
            json_body=body,
        )
        if response.status_code != 200:
            err_detail = self._parse_api_error(response)
            self.log(f"OpenAI images.edit error {response.status_code}: {err_detail}")
            return Message(
                text=f"OpenAI API error {response.status_code}: {err_detail}",
                category="error",
            )

        data = response.json()
        return data.get("data", [{}])[0]

    def _run_generate_flow(
        self,
        prompt: str,
        size: str,
        client: OpenAI,
    ) -> dict:
        """Run generate flow via client.images.generate. Returns image object."""
        kwargs = self._build_generate_kwargs(prompt, size)
        self.log(
            f"OpenAI images.generate: model={kwargs.get('model', '')}\n"
            f"Body: {json.dumps(kwargs, ensure_ascii=False, indent=2)}"
        )
        response = client.images.generate(**kwargs)
        return response.data[0]

    def _extract_b64(self, img: dict | object) -> str | None:
        """Extract b64_json from API response image object."""
        return img.get("b64_json") if isinstance(img, dict) else getattr(img, "b64_json", None)

    def _build_data_url(self, img: dict | object) -> str | None:
        """Build data URL (data:image/...;base64,...) from image. Returns None if b64 not found."""
        b64 = self._extract_b64(img)
        if not b64:
            return None
        fmt = (getattr(self, "output_format", "png") or "png") if self._is_gpt_model() else "png"
        mime = "image/webp" if fmt == "webp" else f"image/{fmt}"
        return f"data:{mime};base64,{b64}"

    def _build_image_message(self, img: dict | object) -> Message | None:
        """Build Message from image response. Returns None if b64 not found."""
        data_url = self._build_data_url(img)
        if not data_url:
            return None
        return Message(text=f'<img src="{data_url}">')

    def _run_generation(self) -> tuple[dict | object | None, str | None]:
        """
        Run generation/edit flow. Returns (img, None) on success or (None, error_msg) on failure.
        """
        try:
            self.validate_inputs()
        except ValueError as e:
            self.log(f"Validation error: {e}")
            return None, str(e)

        api_key = self._get_api_key()
        prompt = self._get_prompt_text().strip()
        file_paths = self._get_resolved_file_paths()
        use_edit = bool(file_paths) and self._is_gpt_model()

        self.status = "Editing..." if use_edit else "Generating..."
        try:
            api_base = self._get_api_base()
            client = OpenAI(api_key=api_key, base_url=api_base, timeout=self._REQUEST_TIMEOUT)
            size = self._get_size()

            if use_edit:
                result_edit = self._run_edit_flow(prompt, file_paths, api_key, api_base, size)
                if isinstance(result_edit, Message):
                    return None, result_edit.text
                img = result_edit
            else:
                img = self._run_generate_flow(prompt, size, client)

            data_url = self._build_data_url(img)
            if not data_url:
                return None, "Error: data not found"

            self.status = "Image created"
            return img, None
        except Exception as e:
            self.log(f"OpenAI Images failed: {str(e)}")
            self.status = f"Error: {e}"
            return None, str(e)

    # --- Main ---

    def get_generated_image(self) -> Data:
        """
        Returns Data with raw base64 image.
        Format: base64, format, width, height.
        """
        img, error = self._run_generation()
        if error:
            return Data(data={"error": error})

        b64 = self._extract_b64(img)
        if not b64:
            return Data(data={"error": "Error: data not found"})

        fmt = (getattr(self, "output_format", "png") or "png") if self._is_gpt_model() else "png"
        size = self._get_size()
        width, height = self._parse_size(size)
        if width is None and height is None:
            width, height = self._get_image_dimensions(b64, fmt)

        out = {
            "base64": b64,
            "format": fmt,
            "width": width,
            "height": height,
        }
        return Data(data=out)

    def get_image_message(self) -> Message:
        """
        Returns Message with HTML img tag (data URL) or error message.
        """
        img, error = self._run_generation()
        if error:
            return Message(text=error, category="error")

        result = self._build_image_message(img)
        return result if result else Message(text="Error: data not found", category="error")
