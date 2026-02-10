from lfx.custom import Component
from lfx.io import DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema import Data
from lfx.schema.message import Message
import base64
import requests


class ModelTTS(Component):
    display_name = "TTS"
    description = "Converts text to speech using multiple TTS providers with model selection."
    icon = "book-audio"
    name = "ModelTTSComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
        "ElevenLabs",
        "Google",
    ]

    TTS_MODELS_BY_PROVIDER = {
        "OpenAI": ["tts-1", "tts-1-hd"],
        "OpenAI-Compatible": ["tts-1", "tts-1-hd"],
        "ElevenLabs": ["eleven_multilingual_v2", "eleven_turbo_v2"],
        "Google": ["standard", "wavenet", "neural2"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with TTS capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the TTS model.",
            options=[*TTS_MODELS_BY_PROVIDER["OpenAI"]],
            value="tts-1",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
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
            name="text",
            display_name="Text to Synthesize",
            info="Text that will be converted to speech.",
            required=True,
        ),
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice.",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy",
            advanced=True,
        ),
        DropdownInput(
            name="format",
            display_name="Audio Format",
            info="Select audio format.",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3",
            advanced=True,
        ),
        DropdownInput(
            name="speed",
            display_name="Speed",
            info="Speed of the generated audio. Values range from 0.25 to 4.0.",
            options=["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "3.5", "4.0"],
            value="1.0",
            advanced=True,
        ),
        StrInput(
            name="elevenlabs_voice_id",
            display_name="ElevenLabs Voice ID",
            info="Voice ID from ElevenLabs dashboard.",
            required=False,
            show=False,
            advanced=True,
        ),
        DropdownInput(
            name="elevenlabs_model_id",
            display_name="ElevenLabs Model",
            info="ElevenLabs model for synthesis.",
            options=[*TTS_MODELS_BY_PROVIDER["ElevenLabs"]],
            value="eleven_multilingual_v2",
            show=False,
            advanced=True,
        ),
        StrInput(
            name="elevenlabs_stability",
            display_name="ElevenLabs Stability",
            info="Stability (0.0 - 1.0).",
            value="0.5",
            show=False,
            advanced=True,
        ),
        StrInput(
            name="elevenlabs_similarity_boost",
            display_name="ElevenLabs Similarity Boost",
            info="Similarity boost (0.0 - 1.0).",
            value="0.75",
            show=False,
            advanced=True,

        ),
        StrInput(
            name="google_language_code",
            display_name="Google Language Code",
            info="Language code (e.g. en-US, pt-BR).",
            value="en-US",
            show=False,
            advanced=True,
        ),
        StrInput(
            name="google_voice_name",
            display_name="Google Voice Name",
            info="Optional specific voice name (e.g. en-US-Wavenet-D).",
            value="",
            show=False,
            advanced=True,
        ),
        DropdownInput(
            name="google_ssml_gender",
            display_name="Google SSML Gender",
            info="Voice gender for Google TTS.",
            options=["SSML_VOICE_GENDER_UNSPECIFIED", "MALE", "FEMALE", "NEUTRAL"],
            value="SSML_VOICE_GENDER_UNSPECIFIED",
            show=False,
            advanced=True,
        ),
        DropdownInput(
            name="google_audio_encoding",
            display_name="Google Audio Encoding",
            info="Audio encoding for Google TTS.",
            options=["MP3", "OGG_OPUS", "LINEAR16"],
            value="MP3",
            show=False,
            advanced=True,
        ),
        StrInput(
            name="google_speaking_rate",
            display_name="Google Speaking Rate",
            info="Speaking rate (0.25 - 4.0).",
            value="1.0",
            show=False,
            advanced=True,
        ),
        StrInput(
            name="google_pitch",
            display_name="Google Pitch",
            info="Pitch (-20.0 - 20.0).",
            value="0.0",
            show=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="audio_data",
            display_name="Audio Data",
            method="generate_audio",
        ),
        Output(
            name="base64_text",
            display_name="Base64",
            method="get_base64_text",
        ),
        Output(
            name="audio_link",
            display_name="Data URI",
            method="get_audio_link",
        ),
        Output(
            name="markdown_output",
            display_name="Markdown",
            method="generate_markdown",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.TTS_MODELS_BY_PROVIDER.get(provider, ["tts-1"])

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

            openai_visible = provider in ("OpenAI", "OpenAI-Compatible")
            eleven_visible = provider == "ElevenLabs"
            google_visible = provider == "Google"

            for field in ("voice", "format", "speed"):
                if field in build_config:
                    build_config[field]["show"] = openai_visible

            for field in (
                "elevenlabs_voice_id",
                "elevenlabs_model_id",
                "elevenlabs_stability",
                "elevenlabs_similarity_boost",
            ):
                if field in build_config:
                    build_config[field]["show"] = eleven_visible

            for field in (
                "google_language_code",
                "google_voice_name",
                "google_ssml_gender",
                "google_audio_encoding",
                "google_speaking_rate",
                "google_pitch",
            ):
                if field in build_config:
                    build_config[field]["show"] = google_visible

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "tts-1"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_tts_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/audio/speech"
        return f"{base}/v1/audio/speech"

    def _generate_audio_internal(self) -> dict:
        if not self.api_key:
            return {"error": "API key is required."}

        if hasattr(self.text, "text"):
            text_content = self.text.text
        else:
            text_content = str(self.text)

        if not text_content or not text_content.strip():
            return {"error": "Text input is required."}

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()

        if not api_key:
            return {"error": "A valid API key is required."}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        text = text_content.strip()

        if provider == "ElevenLabs":
            return self._generate_elevenlabs_audio(api_key, text)

        if provider == "Google":
            return self._generate_google_audio(api_key, text)

        voice = getattr(self, "voice", "alloy") or "alloy"
        format_ = getattr(self, "format", "mp3") or "mp3"
        speed = getattr(self, "speed", "1.0") or "1.0"
        model = self._normalize_model(getattr(self, "model", "tts-1"))
        url = self._build_tts_url(getattr(self, "base_url", "https://api.openai.com/v1"))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": format_,
            "speed": float(speed),
        }

        try:
            self.status = f"Generating audio with model '{model}', voice '{voice}'..."
            self.log(f"Making TTS request with model: {model}, voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "speed": speed,
                    "model": model,
                    "provider": provider,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_elevenlabs_audio(self, api_key: str, text: str) -> dict:
        voice_id = getattr(self, "elevenlabs_voice_id", "") or ""
        model_id = getattr(self, "elevenlabs_model_id", "eleven_multilingual_v2") or "eleven_multilingual_v2"
        stability = getattr(self, "elevenlabs_stability", "0.5") or "0.5"
        similarity_boost = getattr(self, "elevenlabs_similarity_boost", "0.75") or "0.75"

        if not voice_id:
            return {"error": "ElevenLabs voice ID is required."}

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float(stability),
                "similarity_boost": float(similarity_boost),
            },
        }

        try:
            self.status = f"Generating audio with ElevenLabs model '{model_id}'..."
            self.log(f"Making ElevenLabs request with model: {model_id}, voice_id: {voice_id}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": "mp3",
                    "voice": voice_id,
                    "model": model_id,
                    "provider": "ElevenLabs",
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_google_audio(self, api_key: str, text: str) -> dict:
        language_code = getattr(self, "google_language_code", "en-US") or "en-US"
        voice_name = getattr(self, "google_voice_name", "") or ""
        ssml_gender = getattr(self, "google_ssml_gender", "SSML_VOICE_GENDER_UNSPECIFIED")
        audio_encoding = getattr(self, "google_audio_encoding", "MP3") or "MP3"
        speaking_rate = getattr(self, "google_speaking_rate", "1.0") or "1.0"
        pitch = getattr(self, "google_pitch", "0.0") or "0.0"

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        headers = {"Content-Type": "application/json"}

        voice_payload = {
            "languageCode": language_code,
            "ssmlGender": ssml_gender,
        }
        if voice_name:
            voice_payload["name"] = voice_name

        payload = {
            "input": {"text": text},
            "voice": voice_payload,
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": float(speaking_rate),
                "pitch": float(pitch),
            },
        }

        try:
            self.status = f"Generating audio with Google TTS ({audio_encoding})..."
            self.log(f"Making Google TTS request with language: {language_code}, voice: {voice_name or 'default'}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                json_data = response.json()
                audio_base64 = json_data.get("audioContent")
                if not audio_base64:
                    error_msg = "Google TTS response missing audioContent."
                    self.status = f"Error: {error_msg}"
                    return {"error": error_msg}

                audio_content = base64.b64decode(audio_base64)
                audio_size_kb = len(audio_content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(audio_content)} bytes")

                format_ = "mp3" if audio_encoding == "MP3" else "wav"
                if audio_encoding == "OGG_OPUS":
                    format_ = "opus"

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice_name or language_code,
                    "model": getattr(self, "model", "standard"),
                    "provider": "Google",
                    "size_bytes": len(audio_content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": audio_content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def generate_audio(self) -> Data:
        result = self._generate_audio_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        output_data = {k: v for k, v in result.items() if k != "audio_content"}
        return Data(data=output_data)

    def get_base64_text(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result["audio_base64"])

    def get_audio_link(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        return Message(text=data_uri)

    def generate_markdown(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        html_code = (
            "<audio controls>\n"
            f'  <source src="{data_uri}" type="{mime_type}">\n'
            "</audio>"
        )
        return Message(text=html_code)

    def generate_markdown(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        html_code = (
            "<audio controls>\n"
            f'  <source src="{data_uri}" type="{mime_type}">\n'
            "</audio>"
        )
        return Message(text=html_code)

    def generate_markdown(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        html_code = (
            "<audio controls>\n"
            f'  <source src="{data_uri}" type="{mime_type}">\n'
            "</audio>"
        )
        return Message(text=html_code)


    def generate_markdown(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        html_code = (
            "<audio controls>\n"
            f'  <source src="{data_uri}" type="{mime_type}">\n'
            "</audio>"
        )
        return Message(text=html_code)
from lfx.custom import Component
from lfx.io import DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema import Data
from lfx.schema.message import Message
import base64
import requests


class ModelTTS(Component):
    display_name = "Model TTS"
    description = "Converts text to speech using multiple TTS providers with model selection."
    icon = "volume-high"
    name = "ModelTTSComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
        "ElevenLabs",
        "Google",
    ]

    TTS_MODELS_BY_PROVIDER = {
        "OpenAI": ["tts-1", "tts-1-hd"],
        "OpenAI-Compatible": ["tts-1", "tts-1-hd"],
        "ElevenLabs": ["eleven_multilingual_v2", "eleven_turbo_v2"],
        "Google": ["standard", "wavenet", "neural2"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with TTS capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="TTS Model",
            info="Select the TTS model.",
            options=[*TTS_MODELS_BY_PROVIDER["OpenAI"]],
            value="tts-1",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
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
            name="text",
            display_name="Text to Synthesize",
            info="Text that will be converted to speech.",
            required=True,
        ),
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice.",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy",
        ),
        DropdownInput(
            name="format",
            display_name="Audio Format",
            info="Select audio format.",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3",
        ),
        DropdownInput(
            name="speed",
            display_name="Speed",
            info="Speed of the generated audio. Values range from 0.25 to 4.0.",
            options=["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "3.5", "4.0"],
            value="1.0",
        ),
        StrInput(
            name="elevenlabs_voice_id",
            display_name="ElevenLabs Voice ID",
            info="Voice ID from ElevenLabs dashboard.",
            required=False,
            show=False,
        ),
        DropdownInput(
            name="elevenlabs_model_id",
            display_name="ElevenLabs Model",
            info="ElevenLabs model for synthesis.",
            options=[*TTS_MODELS_BY_PROVIDER["ElevenLabs"]],
            value="eleven_multilingual_v2",
            show=False,
        ),
        StrInput(
            name="elevenlabs_stability",
            display_name="ElevenLabs Stability",
            info="Stability (0.0 - 1.0).",
            value="0.5",
            show=False,
        ),
        StrInput(
            name="elevenlabs_similarity_boost",
            display_name="ElevenLabs Similarity Boost",
            info="Similarity boost (0.0 - 1.0).",
            value="0.75",
            show=False,
        ),
        StrInput(
            name="google_language_code",
            display_name="Google Language Code",
            info="Language code (e.g. en-US, pt-BR).",
            value="en-US",
            show=False,
        ),
        StrInput(
            name="google_voice_name",
            display_name="Google Voice Name",
            info="Optional specific voice name (e.g. en-US-Wavenet-D).",
            value="",
            show=False,
        ),
        DropdownInput(
            name="google_ssml_gender",
            display_name="Google SSML Gender",
            info="Voice gender for Google TTS.",
            options=["SSML_VOICE_GENDER_UNSPECIFIED", "MALE", "FEMALE", "NEUTRAL"],
            value="SSML_VOICE_GENDER_UNSPECIFIED",
            show=False,
        ),
        DropdownInput(
            name="google_audio_encoding",
            display_name="Google Audio Encoding",
            info="Audio encoding for Google TTS.",
            options=["MP3", "OGG_OPUS", "LINEAR16"],
            value="MP3",
            show=False,
        ),
        StrInput(
            name="google_speaking_rate",
            display_name="Google Speaking Rate",
            info="Speaking rate (0.25 - 4.0).",
            value="1.0",
            show=False,
        ),
        StrInput(
            name="google_pitch",
            display_name="Google Pitch",
            info="Pitch (-20.0 - 20.0).",
            value="0.0",
            show=False,
        ),
    ]

    outputs = [
        Output(
            name="audio_data",
            display_name="Audio Data",
            method="generate_audio",
        ),
        Output(
            name="base64_text",
            display_name="Base64",
            method="get_base64_text",
        ),
        Output(
            name="audio_link",
            display_name="Data URI",
            method="get_audio_link",
        ),
        Output(
            name="markdown_output",
            display_name="Markdown",
            method="generate_markdown",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.TTS_MODELS_BY_PROVIDER.get(provider, ["tts-1"])

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

            openai_visible = provider in ("OpenAI", "OpenAI-Compatible")
            eleven_visible = provider == "ElevenLabs"
            google_visible = provider == "Google"

            for field in ("voice", "format", "speed"):
                if field in build_config:
                    build_config[field]["show"] = openai_visible

            for field in (
                "elevenlabs_voice_id",
                "elevenlabs_model_id",
                "elevenlabs_stability",
                "elevenlabs_similarity_boost",
            ):
                if field in build_config:
                    build_config[field]["show"] = eleven_visible

            for field in (
                "google_language_code",
                "google_voice_name",
                "google_ssml_gender",
                "google_audio_encoding",
                "google_speaking_rate",
                "google_pitch",
            ):
                if field in build_config:
                    build_config[field]["show"] = google_visible

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "tts-1"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_tts_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/audio/speech"
        return f"{base}/v1/audio/speech"

    def _generate_audio_internal(self) -> dict:
        if not self.api_key:
            return {"error": "API key is required."}

        if hasattr(self.text, "text"):
            text_content = self.text.text
        else:
            text_content = str(self.text)

        if not text_content or not text_content.strip():
            return {"error": "Text input is required."}

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()

        if not api_key:
            return {"error": "A valid API key is required."}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        text = text_content.strip()

        if provider == "ElevenLabs":
            return self._generate_elevenlabs_audio(api_key, text)

        if provider == "Google":
            return self._generate_google_audio(api_key, text)

        voice = getattr(self, "voice", "alloy") or "alloy"
        format_ = getattr(self, "format", "mp3") or "mp3"
        speed = getattr(self, "speed", "1.0") or "1.0"
        model = self._normalize_model(getattr(self, "model", "tts-1"))
        url = self._build_tts_url(getattr(self, "base_url", "https://api.openai.com/v1"))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": format_,
            "speed": float(speed),
        }

        try:
            self.status = f"Generating audio with model '{model}', voice '{voice}'..."
            self.log(f"Making TTS request with model: {model}, voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "speed": speed,
                    "model": model,
                    "provider": provider,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_elevenlabs_audio(self, api_key: str, text: str) -> dict:
        voice_id = getattr(self, "elevenlabs_voice_id", "") or ""
        model_id = getattr(self, "elevenlabs_model_id", "eleven_multilingual_v2") or "eleven_multilingual_v2"
        stability = getattr(self, "elevenlabs_stability", "0.5") or "0.5"
        similarity_boost = getattr(self, "elevenlabs_similarity_boost", "0.75") or "0.75"

        if not voice_id:
            return {"error": "ElevenLabs voice ID is required."}

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float(stability),
                "similarity_boost": float(similarity_boost),
            },
        }

        try:
            self.status = f"Generating audio with ElevenLabs model '{model_id}'..."
            self.log(f"Making ElevenLabs request with model: {model_id}, voice_id: {voice_id}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": "mp3",
                    "voice": voice_id,
                    "model": model_id,
                    "provider": "ElevenLabs",
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_google_audio(self, api_key: str, text: str) -> dict:
        language_code = getattr(self, "google_language_code", "en-US") or "en-US"
        voice_name = getattr(self, "google_voice_name", "") or ""
        ssml_gender = getattr(self, "google_ssml_gender", "SSML_VOICE_GENDER_UNSPECIFIED")
        audio_encoding = getattr(self, "google_audio_encoding", "MP3") or "MP3"
        speaking_rate = getattr(self, "google_speaking_rate", "1.0") or "1.0"
        pitch = getattr(self, "google_pitch", "0.0") or "0.0"

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        headers = {"Content-Type": "application/json"}

        voice_payload = {
            "languageCode": language_code,
            "ssmlGender": ssml_gender,
        }
        if voice_name:
            voice_payload["name"] = voice_name

        payload = {
            "input": {"text": text},
            "voice": voice_payload,
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": float(speaking_rate),
                "pitch": float(pitch),
            },
        }

        try:
            self.status = f"Generating audio with Google TTS ({audio_encoding})..."
            self.log(f"Making Google TTS request with language: {language_code}, voice: {voice_name or 'default'}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                json_data = response.json()
                audio_base64 = json_data.get("audioContent")
                if not audio_base64:
                    error_msg = "Google TTS response missing audioContent."
                    self.status = f"Error: {error_msg}"
                    return {"error": error_msg}

                audio_content = base64.b64decode(audio_base64)
                audio_size_kb = len(audio_content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(audio_content)} bytes")

                format_ = "mp3" if audio_encoding == "MP3" else "wav"
                if audio_encoding == "OGG_OPUS":
                    format_ = "opus"

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice_name or language_code,
                    "model": getattr(self, "model", "standard"),
                    "provider": "Google",
                    "size_bytes": len(audio_content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": audio_content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def generate_audio(self) -> Data:
        result = self._generate_audio_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        output_data = {k: v for k, v in result.items() if k != "audio_content"}
        return Data(data=output_data)

    def get_base64_text(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result["audio_base64"])

    def get_audio_link(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        return Message(text=data_uri)
from lfx.custom import Component
from lfx.io import DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema import Data
from lfx.schema.message import Message
import base64
import requests


class ModelTTS(Component):
    display_name = "Model TTS"
    description = "Converts text to speech using multiple TTS providers with model selection."
    icon = "volume-high"
    name = "ModelTTSComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
        "ElevenLabs",
        "Google",
    ]

    TTS_MODELS_BY_PROVIDER = {
        "OpenAI": ["tts-1", "tts-1-hd"],
        "OpenAI-Compatible": ["tts-1", "tts-1-hd"],
        "ElevenLabs": ["eleven_multilingual_v2", "eleven_turbo_v2"],
        "Google": ["standard", "wavenet", "neural2"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with TTS capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="TTS Model",
            info="Select the TTS model.",
            options=[*TTS_MODELS_BY_PROVIDER["OpenAI"]],
            value="tts-1",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
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
            name="text",
            display_name="Text to Synthesize",
            info="Text that will be converted to speech.",
            required=True,
        ),
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice.",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy",
        ),
        DropdownInput(
            name="format",
            display_name="Audio Format",
            info="Select audio format.",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3",
        ),
        DropdownInput(
            name="speed",
            display_name="Speed",
            info="Speed of the generated audio. Values range from 0.25 to 4.0.",
            options=["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "3.5", "4.0"],
            value="1.0",
        ),
        StrInput(
            name="elevenlabs_voice_id",
            display_name="ElevenLabs Voice ID",
            info="Voice ID from ElevenLabs dashboard.",
            required=False,
            show=False,
        ),
        DropdownInput(
            name="elevenlabs_model_id",
            display_name="ElevenLabs Model",
            info="ElevenLabs model for synthesis.",
            options=[*TTS_MODELS_BY_PROVIDER["ElevenLabs"]],
            value="eleven_multilingual_v2",
            show=False,
        ),
        StrInput(
            name="elevenlabs_stability",
            display_name="ElevenLabs Stability",
            info="Stability (0.0 - 1.0).",
            value="0.5",
            show=False,
        ),
        StrInput(
            name="elevenlabs_similarity_boost",
            display_name="ElevenLabs Similarity Boost",
            info="Similarity boost (0.0 - 1.0).",
            value="0.75",
            show=False,
        ),
        StrInput(
            name="google_language_code",
            display_name="Google Language Code",
            info="Language code (e.g. en-US, pt-BR).",
            value="en-US",
            show=False,
        ),
        StrInput(
            name="google_voice_name",
            display_name="Google Voice Name",
            info="Optional specific voice name (e.g. en-US-Wavenet-D).",
            value="",
            show=False,
        ),
        DropdownInput(
            name="google_ssml_gender",
            display_name="Google SSML Gender",
            info="Voice gender for Google TTS.",
            options=["SSML_VOICE_GENDER_UNSPECIFIED", "MALE", "FEMALE", "NEUTRAL"],
            value="SSML_VOICE_GENDER_UNSPECIFIED",
            show=False,
        ),
        DropdownInput(
            name="google_audio_encoding",
            display_name="Google Audio Encoding",
            info="Audio encoding for Google TTS.",
            options=["MP3", "OGG_OPUS", "LINEAR16"],
            value="MP3",
            show=False,
        ),
        StrInput(
            name="google_speaking_rate",
            display_name="Google Speaking Rate",
            info="Speaking rate (0.25 - 4.0).",
            value="1.0",
            show=False,
        ),
        StrInput(
            name="google_pitch",
            display_name="Google Pitch",
            info="Pitch (-20.0 - 20.0).",
            value="0.0",
            show=False,
        ),
    ]

    outputs = [
        Output(
            name="audio_data",
            display_name="Audio Data",
            method="generate_audio",
        ),
        Output(
            name="base64_text",
            display_name="Base64",
            method="get_base64_text",
        ),
        Output(
            name="audio_link",
            display_name="Data URI",
            method="get_audio_link",
        ),
        Output(
            name="markdown_output",
            display_name="Markdown",
            method="generate_markdown",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.TTS_MODELS_BY_PROVIDER.get(provider, ["tts-1"])

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

            openai_visible = provider in ("OpenAI", "OpenAI-Compatible")
            eleven_visible = provider == "ElevenLabs"
            google_visible = provider == "Google"

            for field in ("voice", "format", "speed"):
                if field in build_config:
                    build_config[field]["show"] = openai_visible

            for field in (
                "elevenlabs_voice_id",
                "elevenlabs_model_id",
                "elevenlabs_stability",
                "elevenlabs_similarity_boost",
            ):
                if field in build_config:
                    build_config[field]["show"] = eleven_visible

            for field in (
                "google_language_code",
                "google_voice_name",
                "google_ssml_gender",
                "google_audio_encoding",
                "google_speaking_rate",
                "google_pitch",
            ):
                if field in build_config:
                    build_config[field]["show"] = google_visible

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "tts-1"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_tts_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/audio/speech"
        return f"{base}/v1/audio/speech"

    def _generate_audio_internal(self) -> dict:
        if not self.api_key:
            return {"error": "API key is required."}

        if hasattr(self.text, "text"):
            text_content = self.text.text
        else:
            text_content = str(self.text)

        if not text_content or not text_content.strip():
            return {"error": "Text input is required."}

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()

        if not api_key:
            return {"error": "A valid API key is required."}

        provider = getattr(self, "provider", "OpenAI") or "OpenAI"
        text = text_content.strip()

        if provider == "ElevenLabs":
            return self._generate_elevenlabs_audio(api_key, text)

        if provider == "Google":
            return self._generate_google_audio(api_key, text)

        voice = getattr(self, "voice", "alloy") or "alloy"
        format_ = getattr(self, "format", "mp3") or "mp3"
        speed = getattr(self, "speed", "1.0") or "1.0"
        model = self._normalize_model(getattr(self, "model", "tts-1"))
        url = self._build_tts_url(getattr(self, "base_url", "https://api.openai.com/v1"))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": format_,
            "speed": float(speed),
        }

        try:
            self.status = f"Generating audio with model '{model}', voice '{voice}'..."
            self.log(f"Making TTS request with model: {model}, voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "speed": speed,
                    "model": model,
                    "provider": provider,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_elevenlabs_audio(self, api_key: str, text: str) -> dict:
        voice_id = getattr(self, "elevenlabs_voice_id", "") or ""
        model_id = getattr(self, "elevenlabs_model_id", "eleven_multilingual_v2") or "eleven_multilingual_v2"
        stability = getattr(self, "elevenlabs_stability", "0.5") or "0.5"
        similarity_boost = getattr(self, "elevenlabs_similarity_boost", "0.75") or "0.75"

        if not voice_id:
            return {"error": "ElevenLabs voice ID is required."}

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float(stability),
                "similarity_boost": float(similarity_boost),
            },
        }

        try:
            self.status = f"Generating audio with ElevenLabs model '{model_id}'..."
            self.log(f"Making ElevenLabs request with model: {model_id}, voice_id: {voice_id}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": "mp3",
                    "voice": voice_id,
                    "model": model_id,
                    "provider": "ElevenLabs",
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def _generate_google_audio(self, api_key: str, text: str) -> dict:
        language_code = getattr(self, "google_language_code", "en-US") or "en-US"
        voice_name = getattr(self, "google_voice_name", "") or ""
        ssml_gender = getattr(self, "google_ssml_gender", "SSML_VOICE_GENDER_UNSPECIFIED")
        audio_encoding = getattr(self, "google_audio_encoding", "MP3") or "MP3"
        speaking_rate = getattr(self, "google_speaking_rate", "1.0") or "1.0"
        pitch = getattr(self, "google_pitch", "0.0") or "0.0"

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        headers = {"Content-Type": "application/json"}

        voice_payload = {
            "languageCode": language_code,
            "ssmlGender": ssml_gender,
        }
        if voice_name:
            voice_payload["name"] = voice_name

        payload = {
            "input": {"text": text},
            "voice": voice_payload,
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": float(speaking_rate),
                "pitch": float(pitch),
            },
        }

        try:
            self.status = f"Generating audio with Google TTS ({audio_encoding})..."
            self.log(f"Making Google TTS request with language: {language_code}, voice: {voice_name or 'default'}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                json_data = response.json()
                audio_base64 = json_data.get("audioContent")
                if not audio_base64:
                    error_msg = "Google TTS response missing audioContent."
                    self.status = f"Error: {error_msg}"
                    return {"error": error_msg}

                audio_content = base64.b64decode(audio_base64)
                audio_size_kb = len(audio_content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(audio_content)} bytes")

                format_ = "mp3" if audio_encoding == "MP3" else "wav"
                if audio_encoding == "OGG_OPUS":
                    format_ = "opus"

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice_name or language_code,
                    "model": getattr(self, "model", "standard"),
                    "provider": "Google",
                    "size_bytes": len(audio_content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": audio_content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def generate_audio(self) -> Data:
        result = self._generate_audio_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        output_data = {k: v for k, v in result.items() if k != "audio_content"}
        return Data(data=output_data)

    def get_base64_text(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result["audio_base64"])

    def get_audio_link(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        return Message(text=data_uri)
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
import base64
import requests


class TTSComponent(Component):
    display_name = "TTS"
    description = "Converts text to speech using an OpenAI-compatible TTS endpoint with model selection."
    icon = "volume"
    name = "TTSComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
    ]

    TTS_MODELS_BY_PROVIDER = {
        "OpenAI": ["tts-1", "tts-1-hd"],
        "OpenAI-Compatible": ["tts-1", "tts-1-hd"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with TTS capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="TTS Model",
            info="Select the TTS model.",
            options=[*TTS_MODELS_BY_PROVIDER["OpenAI"]],
            value="tts-1",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
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
            name="text",
            display_name="Text to Synthesize",
            info="Text that will be converted to speech.",
            required=True,
        ),
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice.",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy",
        ),
        DropdownInput(
            name="format",
            display_name="Audio Format",
            info="Select audio format.",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3",
        ),
        DropdownInput(
            name="speed",
            display_name="Speed",
            info="Speed of the generated audio. Values range from 0.25 to 4.0.",
            options=["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "3.5", "4.0"],
            value="1.0",
        ),
    ]

    outputs = [
        Output(
            name="audio_data",
            display_name="Audio Data",
            method="generate_audio",
        ),
        Output(
            name="base64_text",
            display_name="Base64",
            method="get_base64_text",
        ),
        Output(
            name="audio_link",
            display_name="Data URI",
            method="get_audio_link",
        ),
        Output(
            name="markdown_output",
            display_name="Markdown",
            method="generate_markdown",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.TTS_MODELS_BY_PROVIDER.get(provider, ["tts-1"])

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
            return "tts-1"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_tts_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/audio/speech"
        return f"{base}/v1/audio/speech"

    def _generate_audio_internal(self) -> dict:
        if not self.api_key:
            return {"error": "API key is required."}

        if hasattr(self.text, "text"):
            text_content = self.text.text
        else:
            text_content = str(self.text)

        if not text_content or not text_content.strip():
            return {"error": "Text input is required."}

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()

        if not api_key:
            return {"error": "A valid API key is required."}

        text = text_content.strip()
        voice = getattr(self, "voice", "alloy") or "alloy"
        format_ = getattr(self, "format", "mp3") or "mp3"
        speed = getattr(self, "speed", "1.0") or "1.0"
        model = self._normalize_model(getattr(self, "model", "tts-1"))
        url = self._build_tts_url(getattr(self, "base_url", "https://api.openai.com/v1"))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": format_,
            "speed": float(speed),
        }

        try:
            self.status = f"Generating audio with model '{model}', voice '{voice}'..."
            self.log(f"Making TTS request with model: {model}, voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                audio_size_kb = len(response.content) / 1024

                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")

                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "speed": speed,
                    "model": model,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content,
                }

            error_msg = f"API Error {response.status_code}: {response.text}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = f"Error: {error_msg}"
            return {"error": error_msg}

    def generate_audio(self) -> Data:
        result = self._generate_audio_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        output_data = {k: v for k, v in result.items() if k != "audio_content"}
        return Data(data=output_data)

    def get_base64_text(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result["audio_base64"])

    def get_audio_link(self) -> Message:
        result = self._generate_audio_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")

        format_ = result["format"]
        mime_type = f"audio/{format_}"

        if format_ == "mp3":
            mime_type = "audio/mpeg"
        elif format_ == "wav":
            mime_type = "audio/wav"
        elif format_ == "ogg":
            mime_type = "audio/ogg"
        elif format_ == "flac":
            mime_type = "audio/flac"
        elif format_ == "aac":
            mime_type = "audio/aac"
        elif format_ == "opus":
            mime_type = "audio/opus"
        elif format_ == "pcm":
            mime_type = "audio/pcm"

        data_uri = f"data:{mime_type};base64,{result['audio_base64']}"
        return Message(text=data_uri)
