from langflow.custom import Component
from langflow.io import FileInput, SecretStrInput, StrInput, DropdownInput, BoolInput, Output, FloatInput
from langflow.schema import Data
import requests
import json


class SunoUploadCoverComponent(Component):
    display_name = "Suno Upload & Cover"
    description = "Uploads audio and triggers a cover generation using the Suno API with async callback."
    icon = "upload"
    name = "SunoUploadCoverComponent"

    field_order = [
        "api_key", "upload_url", "prompt", "style", "title", "custom_mode",
        "instrumental", "model", "negative_tags", "vocal_gender", "style_weight",
        "weirdness_constraint", "audio_weight", "callback_url"
    ]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Your Suno API key.",
            required=True,
        ),
        StrInput(
            name="upload_url",
            display_name="Upload URL",
            info="URL where the audio file is stored (must be public or pre-signed).",
            required=True,
        ),
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="Prompt describing the desired musical style.",
            required=True,
        ),
        StrInput(
            name="style",
            display_name="Style",
            info="Musical style to apply.",
            required=True,
        ),
        StrInput(
            name="title",
            display_name="Title",
            info="Title of the track.",
            required=True,
        ),
        BoolInput(
            name="custom_mode",
            display_name="Custom Mode",
            info="Enable custom generation mode.",
            value=True
        ),
        BoolInput(
            name="instrumental",
            display_name="Instrumental",
            info="Generate as instrumental only.",
            value=True
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            options=["V3_5", "V2"],
            value="V3_5",
            info="Model version to use."
        ),
        StrInput(
            name="negative_tags",
            display_name="Negative Tags",
            info="Comma-separated tags to avoid in the generation.",
            value=""
        ),
        DropdownInput(
            name="vocal_gender",
            display_name="Vocal Gender",
            options=["m", "f"],
            value="m",
            info="Gender of the vocals."
        ),
        FloatInput(
            name="style_weight",
            display_name="Style Weight",
            value=0.65,
            info="Weight for the style adherence."
        ),
        FloatInput(
            name="weirdness_constraint",
            display_name="Weirdness Constraint",
            value=0.65,
            info="Control how unusual the output can be."
        ),
        FloatInput(
            name="audio_weight",
            display_name="Audio Weight",
            value=0.65,
            info="How much to adhere to uploaded audio."
        ),
        StrInput(
            name="callback_url",
            display_name="Callback URL",
            info="Public URL where the Suno API should send the result. Must accept POST requests.",
            required=True,
        ),
    ]

    outputs = [
        Output(
            name="submission_status",
            display_name="Submission Status",
            method="upload_and_cover",
        ),
    ]

    def upload_and_cover(self) -> Data:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "uploadUrl": self.upload_url,
                "prompt": self.prompt,
                "style": self.style,
                "title": self.title,
                "customMode": self.custom_mode,
                "instrumental": self.instrumental,
                "model": self.model,
                "negativeTags": self.negative_tags,
                "vocalGender": self.vocal_gender,
                "styleWeight": self.style_weight,
                "weirdnessConstraint": self.weirdness_constraint,
                "audioWeight": self.audio_weight,
                "callBackUrl": self.callback_url,
            }

            self.log("Sending request to Suno API with the following payload:")
            self.log(json.dumps(payload, indent=2))

            response = requests.post(
                "https://api.sunoapi.org/api/v1/generate/upload-cover",
                headers=headers,
                json=payload,
            )
            self.log(f"HTTP Status Code: {response.status_code}")

            try:
                result = response.json()
                self.log("Response JSON from Suno:")
                self.log(json.dumps(result, indent=2))
            except Exception as parse_error:
                self.log(f"Failed to parse JSON response: {parse_error}")
                result = {}

            # Sucesso esperado mesmo sem cover_url, pois será enviado por callback
            if response.status_code == 200:
                message = (
                    "✅ Requisição enviada com sucesso. A URL do cover será enviada para seu endpoint de callback: "
                    f"{self.callback_url}"
                )
                self.status = message
                return Data(data={"status": message})

            # Se o status não for 200, algo deu errado
            error_msg = result.get("msg") or "Unknown error from Suno API."
            raise ValueError(f"API returned error: {error_msg}")

        except Exception as e:
            error_message = f"Error uploading and covering audio: {str(e)}"
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})
