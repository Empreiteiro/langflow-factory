from lfx.custom import Component
from lfx.io import StrInput, MessageInput, SecretStrInput, IntInput, FloatInput, BoolInput, DropdownInput, Output
from lfx.schema import Data
import requests


class GoogleImagenComponent(Component):
    display_name = "Google Imagen"
    description = "Generate images using Google Vertex AI Imagen models (Imagen 3 and Imagen 4)."
    icon = "GoogleGenerativeAI"
    name = "GoogleImagenComponent"
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
        ),
        DropdownInput(
            name="model_name",
            display_name="Model Name",
            info="Select the Imagen model to use for image generation.",
            options=[
                "imagen-3.0-generate-002",
                "imagen-3.0-generate-001", 
                "imagen-3.0-fast-generate-001",
                "imagen-3.0-capability-001",
                "imagen-4.0-generate-preview-06-06",
                "imagen-4.0-fast-generate-preview-06-06",
                "imagen-4.0-ultra-generate-preview-06-06",
            ],
            value="imagen-3.0-generate-002",
        ),
        IntInput(
            name="image_count",
            display_name="Image Count",
            info="Number of images to generate (1-4 for most models, 1 for Imagen 4 Ultra).",
            value=1,
        ),
        FloatInput(
            name="temperature",
            display_name="Temperature",
            info="Controls diversity. Higher values increase randomness (not supported by all models).",
            value=0.4,
        ),
        BoolInput(
            name="safety_filter",
            display_name="Enable Safety Filter",
            info="Enable safety filter for generated images.",
            value=True,
        ),
        StrInput(
            name="aspect_ratio",
            display_name="Aspect Ratio",
            info="Image aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9). Leave empty for default.",
            value="",
        ),
        StrInput(
            name="negative_prompt",
            display_name="Negative Prompt",
            info="What to avoid in the image. Only supported by some models.",
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Generated Images", name="generated_images", method="generate_images"),
    ]

    field_order = [
        "prompt", "api_key", "project_id", "location", "model_name",
        "image_count", "temperature", "safety_filter", "aspect_ratio", "negative_prompt"
    ]

    def _get_model_capabilities(self, model_name: str) -> dict:
        """Get capabilities and limitations for each model"""
        capabilities = {
            # Imagen 3 models
            "imagen-3.0-generate-002": {
                "supports_temperature": False,
                "supports_negative_prompt": True,
                "max_images": 4,
                "generation_type": "generate",
                "status": "GA"
            },
            "imagen-3.0-generate-001": {
                "supports_temperature": False,
                "supports_negative_prompt": True,
                "max_images": 4,
                "generation_type": "generate",
                "status": "GA"
            },
            "imagen-3.0-fast-generate-001": {
                "supports_temperature": False,
                "supports_negative_prompt": True,
                "max_images": 4,
                "generation_type": "generate",
                "status": "GA"
            },
            "imagen-3.0-capability-001": {
                "supports_temperature": False,
                "supports_negative_prompt": True,
                "max_images": 4,
                "generation_type": "capability",
                "status": "GA"
            },
            # Imagen 4 models (Preview)
            "imagen-4.0-generate-preview-06-06": {
                "supports_temperature": False,
                "supports_negative_prompt": False,
                "max_images": 4,
                "generation_type": "generate",
                "status": "Preview"
            },
            "imagen-4.0-fast-generate-preview-06-06": {
                "supports_temperature": False,
                "supports_negative_prompt": False,
                "max_images": 4,
                "generation_type": "generate",
                "status": "Preview"
            },
            "imagen-4.0-ultra-generate-preview-06-06": {
                "supports_temperature": False,
                "supports_negative_prompt": False,
                "max_images": 1,
                "generation_type": "generate",
                "status": "Preview"
            },
        }
        return capabilities.get(model_name, {})

    def _build_payload(self, model_capabilities: dict) -> dict:
        """Build the API payload based on model capabilities"""
        
        # Base payload structure
        payload = {
            "instances": [
                {
                    "prompt": self.prompt,
                }
            ],
            "parameters": {}
        }

        # Add image count if supported
        if model_capabilities.get("max_images", 1) >= self.image_count:
            payload["parameters"]["sampleCount"] = self.image_count
        else:
            payload["parameters"]["sampleCount"] = 1
            self.log(f"Warning: Model {self.model_name} supports max {model_capabilities.get('max_images', 1)} images. Using 1.")

        # Add aspect ratio if provided
        if self.aspect_ratio:
            payload["parameters"]["aspectRatio"] = self.aspect_ratio

        # Add negative prompt if supported and provided
        if model_capabilities.get("supports_negative_prompt", False) and self.negative_prompt:
            payload["instances"][0]["negativePrompt"] = self.negative_prompt

        # Add temperature if supported (legacy parameter for some models)
        if model_capabilities.get("supports_temperature", False):
            payload["instances"][0]["temperature"] = self.temperature

        # Add safety filter settings
        safety_level = "BLOCK_MEDIUM_AND_ABOVE" if self.safety_filter else "BLOCK_NONE"
        payload["parameters"]["safetyFilterLevel"] = safety_level

        return payload

    def generate_images(self) -> Data:
        # Get model capabilities
        model_capabilities = self._get_model_capabilities(self.model_name)
        
        if not model_capabilities:
            error_msg = f"Unknown model: {self.model_name}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})

        # Build the endpoint URL
        endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}:predict"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build payload based on model capabilities
        payload = self._build_payload(model_capabilities)

        try:
            self.log(f"Using {self.model_name} ({model_capabilities.get('status', 'Unknown')}) for image generation")
            
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            predictions = response.json().get("predictions", [])

            if not predictions:
                error_msg = "No predictions returned from the API."
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Extract image data based on response format
            images = []
            for pred in predictions:
                if "bytesBase64Encoded" in pred:
                    # Base64 encoded image
                    images.append({
                        "type": "base64",
                        "data": pred["bytesBase64Encoded"]
                    })
                elif "imageUri" in pred:
                    # Image URI
                    images.append({
                        "type": "uri", 
                        "data": pred["imageUri"]
                    })
                else:
                    # Fallback - return the whole prediction
                    images.append({
                        "type": "raw",
                        "data": pred
                    })

            result_data = {
                "images": images,
                "model_used": self.model_name,
                "model_status": model_capabilities.get('status', 'Unknown'),
                "prompt": self.prompt,
                "count": len(images)
            }

            self.status = f"Generated {len(images)} image(s) using {self.model_name}"
            return Data(data=result_data)

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg += f" - {error_details}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
