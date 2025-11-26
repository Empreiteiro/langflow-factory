from langflow.custom import Component
from langflow.io import StrInput, MessageInput, SecretStrInput, IntInput, FloatInput, BoolInput, DropdownInput, Output
from langflow.schema import Data
import requests


class GoogleImagen2Component(Component):
    display_name = "Google Imagen 2"
    description = "Generate images using Google Vertex AI Gemini 2.5 Flash Image Preview models."
    icon = "GoogleGenerativeAI"
    name = "GoogleImagen2Component"
    beta = True

    inputs = [
        MessageInput(
            name="prompt",
            display_name="Prompt",
            info="Text prompt to generate the image.",
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="Google API Key",
            info="Your Google Cloud API key.",
            required=True,
            real_time_refresh=True,
        ),
        StrInput(
            name="project_id",
            display_name="Project ID",
            info="Your Google Cloud project ID.",
            required=True,
        ),
        StrInput(
            name="location",
            display_name="Location",
            info="The region (like 'us-central1') where the model is deployed.",
            value="us-central1",
            advanced=True,
        ),
        DropdownInput(
            name="model_name",
            display_name="Model Name",
            info="Select the Gemini image generation model to use.",
            options=[
                "gemini-3-pro-image-preview",
                "gemini-2.5-flash-image-preview",
                "gemini-2.0-flash-image-preview",
            ],
            value="gemini-2.5-flash-image-preview",
        ),
        IntInput(
            name="image_count",
            display_name="Image Count",
            info="Number of images to generate.",
            value=1,
        ),
        FloatInput(
            name="temperature",
            display_name="Temperature",
            info="Controls diversity. Higher values increase randomness.",
            value=0.4,
        ),
        BoolInput(
            name="safety_filter",
            display_name="Enable Safety Filter",
            info="Enable safety filter for generated images.",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Generated Images", name="generated_images", method="generate_images"),
    ]

    field_order = [
        "prompt", "api_key", "project_id", "location", "model_name",
        "image_count", "temperature", "safety_filter"
    ]

    def generate_images(self) -> Data:
        endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}:predict"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "instances": [
                {
                    "prompt": self.prompt,
                    "imageCount": self.image_count,
                    "temperature": self.temperature,
                    "safetyFilterLevel": "BLOCK_MEDIUM_AND_ABOVE" if self.safety_filter else "BLOCK_NONE",
                }
            ]
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            predictions = response.json().get("predictions", [])

            if not predictions:
                error_msg = "No predictions returned from the API."
                self.status = error_msg
                return Data(data={"error": error_msg})

            image_urls = [pred.get("imageUri") for pred in predictions]
            return Data(data={"images": image_urls})

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
