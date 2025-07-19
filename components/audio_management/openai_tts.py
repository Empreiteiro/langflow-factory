from langflow.custom import Component
from langflow.io import StrInput, DropdownInput, SecretStrInput, Output
from langflow.schema import Data
from langflow.schema.message import Message
import base64
import requests

class OpenAITTS(Component):
    display_name = "OpenAI TTS"
    description = "Converts text to speech using OpenAI's TTS API."
    icon = "OpenAI"
    name = "OpenAITTSComponent"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="OpenAI API Key",
            info="Your OpenAI API Key.",
            required=True
        ),
        StrInput(
            name="text",
            display_name="Text to Synthesize",
            info="Text that will be converted to speech.",
            required=True
        ),
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice.",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy"
        ),
        DropdownInput(
            name="format",
            display_name="Audio Format",
            info="Select audio format.",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3"
        )
    ]

    outputs = [
        Output(
            name="audio_data",
            display_name="Audio Data",
            method="generate_audio"
        ),
        Output(
            name="base64_text",
            display_name="Base64",
            method="get_base64_text"
        ),
        Output(
            name="audio_link",
            display_name="Data URI",
            method="get_audio_link"
        )
    ]

    def _generate_audio_internal(self) -> dict:
        """Internal method to generate audio and return raw data."""
        # Validate inputs
        if not self.api_key:
            return {"error": "OpenAI API key is required."}
        
        if not self.text or not self.text.strip():
            return {"error": "Text input is required."}

        # Get API key value
        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else str(self.api_key)
        api_key = api_key.strip()
        
        if not api_key or api_key.upper() == "OPENAI_API_KEY":
            return {"error": "A valid OpenAI API key is required."}

        # Prepare request
        text = self.text.strip()
        voice = getattr(self, 'voice', 'alloy') or 'alloy'
        format_ = getattr(self, 'format', 'mp3') or 'mp3'

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice,
            "response_format": format_
        }

        try:
            self.status = f"Generating audio with voice '{voice}' in '{format_}' format..."
            self.log(f"Making TTS request with voice: {voice}, format: {format_}")

            # Make API request
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200 and response.content:
                # Encode audio as base64
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                audio_size_kb = len(response.content) / 1024
                
                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")
                
                return {
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "audio_content": response.content
                }
            else:
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
        """Generate audio from text using OpenAI TTS API."""
        result = self._generate_audio_internal()
        
        if "error" in result:
            return Data(data={"error": result["error"]})
        
        # Remove audio_content from the output (too large for structured data)
        output_data = {k: v for k, v in result.items() if k != "audio_content"}
        return Data(data=output_data)

    def get_base64_text(self) -> Message:
        """Get only the base64 encoded audio as text."""
        result = self._generate_audio_internal()
        
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        
        # Return base64 as text message
        return Message(text=result["audio_base64"])

    def get_audio_link(self) -> Message:
        """Get audio as a data URI link."""
        result = self._generate_audio_internal()
        
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        
        # Create data URI for the audio
        format_ = result["format"]
        mime_type = f"audio/{format_}"
        
        # Handle special cases for MIME types
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