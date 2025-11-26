from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output
from lfx.schema import Data
import requests

class ElevenLabsAudioGenerator(Component):
    display_name = "ElevenLabs Audio Generator"
    description = "Generates audio using ElevenLabs Text-to-Speech API."
    icon = "volume-high"
    name = "ElevenLabsAudioGenerator"
    field_order = ["api_key", "voice_id", "text", "model_id"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Your ElevenLabs API key."
        ),
        StrInput(
            name="voice_id",
            display_name="Voice ID",
            required=True,
            info="The ID of the voice to use. You can find this in your ElevenLabs dashboard."
        ),
        MultilineInput(
            name="text",
            display_name="Text",
            required=True,
            info="The text you want to convert to speech."
        ),
        StrInput(
            name="model_id",
            display_name="Model ID",
            required=False,
            value="eleven_monolingual_v1",
            info="Optional model ID to use for synthesis. Defaults to 'eleven_monolingual_v1'."
        ),
    ]

    outputs = [
        Output(name="audio", display_name="Generated Audio", method="generate_audio")
    ]

    def generate_audio(self) -> Data:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else self.api_key
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": self.text,
                "model_id": self.model_id or "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            self.log(f"Sending request to ElevenLabs API for voice ID: {self.voice_id}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            self.log("Audio generated successfully.")
            return Data(binary_data=response.content, mime_type="audio/mpeg")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with ElevenLabs API: {e}"
            self.status = error_msg
            self.log(error_msg)
            return Data.from_text(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data.from_text(error_msg)
