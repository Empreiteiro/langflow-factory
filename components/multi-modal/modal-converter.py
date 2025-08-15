from typing import Any
import base64
import requests
from openai import OpenAI

from langflow.custom import Component
from langflow.io import HandleInput, Output, TabInput, MessageTextInput, SecretStrInput, DropdownInput, IntInput
from langflow.schema import Data, Message


class ModalConverterComponent(Component):
    display_name = "Modal Converter"
    description = "Convert text to audio, image, or video using AI models."
    icon = "repeat"

    inputs = [
        HandleInput(
            name="input_text",
            display_name="Input",
            input_types=["Message", "Data", "DataFrame"],
            info="Text input to convert to audio, image, or video",
            required=True,
        ),
        TabInput(
            name="output_type",
            display_name="Output Type",
            options=["Audio", "Image", "Video"],
            info="Select the desired output media type",
            real_time_refresh=True,
            value="Audio",
        ),
        DropdownInput(
            name="model_provider",
            display_name="Model Provider",
            options=["OpenAI"],
            value="OpenAI",
            info="Select the AI model provider for processing",
            real_time_refresh=True,
            show=False,
            options_metadata=[{"icon": "OpenAI"}],
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name="OpenAI API Key",
            info="Your OpenAI API key for generating audio, images, and videos",
            required=True,
            show=False,
        ),
        # Audio-specific options
        DropdownInput(
            name="voice",
            display_name="Voice",
            info="Select the voice for audio generation",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            value="alloy",
            advanced=True,
            show=False,
        ),
        DropdownInput(
            name="audio_format",
            display_name="Audio Format",
            info="Select audio format",
            options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
            value="mp3",
            advanced=True,
            show=False,
        ),
        IntInput(
            name="speed",
            display_name="Speed",
            info="Speed of the generated audio. Values range from 0.25 to 4.0.",
            value=1,
            advanced=True,
            show=False,
        ),
        # Image-specific options
        DropdownInput(
            name="image_model",
            display_name="Image Model",
            options=["dall-e-2", "dall-e-3"],
            value="dall-e-3",
            info="The DALL·E model version to use",
            advanced=True,
            show=False,
        ),
        DropdownInput(
            name="image_size",
            display_name="Image Size",
            value="1024x1024",
            info="Size of the generated image",
            options=["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
            advanced=True,
            show=False,
        ),
        IntInput(
            name="num_images",
            display_name="Number of Images",
            value=1,
            info="Number of images to generate",
            advanced=True,
            show=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Audio Data",
            name="audio_output",
            method="generate_audio",
        )
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically show only the relevant output based on the selected output type."""
        if field_name == "output_type":
            # Start with empty outputs
            frontend_node["outputs"] = []

            # Add only the selected output type
            if field_value == "Audio":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Audio Data",
                        name="audio_output",
                        method="generate_audio",
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="Audio Base64",
                        name="audio_base64",
                        method="generate_audio_base64",
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="Playground Audio",
                        name="playground_audio",
                        method="generate_playground_audio",
                    ).to_dict()
                )
            elif field_value == "Image":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Image Data",
                        name="image_output",
                        method="generate_image",
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="Image URL",
                        name="image_url",
                        method="generate_image_url",
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="Playground Image",
                        name="playground_image",
                        method="generate_playground_image",
                    ).to_dict()
                )
            elif field_value == "Video":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Video Data",
                        name="video_output",
                        method="generate_video",
                    ).to_dict()
                )

        return frontend_node

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "output_type":
            # Extract output type from the selected value
            output_type = field_value if isinstance(field_value, str) else "Audio"

            # Define field visibility map
            field_map = {
                "Audio": ["model_provider", "openai_api_key", "voice", "audio_format", "speed"],
                "Image": ["model_provider", "openai_api_key", "image_model", "image_size", "num_images"],
                "Video": ["model_provider", "openai_api_key"],  # No specific fields for video yet
            }

            # Hide all dynamic fields first
            for field_name in ["model_provider", "openai_api_key", "voice", "audio_format", "speed", "image_model", "image_size", "num_images"]:
                if field_name in build_config:
                    build_config[field_name]["show"] = False

            # Show fields based on selected output type
            if output_type in field_map:
                for field_name in field_map[output_type]:
                    if field_name in build_config:
                        build_config[field_name]["show"] = True

        elif field_name == "model_provider":
            # Update API key label based on provider
            if field_value == "OpenAI":
                build_config["openai_api_key"]["display_name"] = "OpenAI API Key"
                build_config["openai_api_key"]["info"] = "Your OpenAI API key for generating audio, images, and videos"
            # Future providers can be added here
            # elif field_value == "Anthropic":
            #     build_config["openai_api_key"]["display_name"] = "Anthropic API Key"
            #     build_config["openai_api_key"]["info"] = "Your Anthropic API key for processing."

        return build_config

    def _extract_text_from_input(self):
        """Extract text from various input types."""
        input_value = self.input_text[0] if isinstance(self.input_text, list) else self.input_text

        # Handle string input
        if isinstance(input_value, str):
            return input_value

        # Handle Message input
        if hasattr(input_value, 'text'):
            return input_value.text

        # Handle Data input
        if hasattr(input_value, 'data'):
            if isinstance(input_value.data, dict) and 'text' in input_value.data:
                return input_value.data['text']
            elif isinstance(input_value.data, str):
                return input_value.data

        # Handle DataFrame input
        if hasattr(input_value, 'to_message'):
            message = input_value.to_message()
            return message.text if hasattr(message, 'text') else str(message)

        # Fallback
        return str(input_value)

    def _get_api_key(self):
        """Get OpenAI API key."""
        api_key = self.openai_api_key
        if hasattr(api_key, 'get_secret_value'):
            return api_key.get_secret_value()
        return str(api_key)

    def generate_audio(self) -> Data:
        """Generate audio from text using OpenAI TTS API."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Data(data={"error": "No text provided for audio generation"})

            api_key = self._get_api_key()
            voice = getattr(self, 'voice', 'alloy') or 'alloy'
            format_ = getattr(self, 'audio_format', 'mp3') or 'mp3'
            speed = getattr(self, 'speed', 1) or 1

            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "response_format": format_,
                "speed": float(speed)
            }

            self.status = f"Generating audio with voice '{voice}' in '{format_}' format at speed {speed}x..."
            self.log(f"Making TTS request with voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                audio_size_kb = len(response.content) / 1024
                
                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")
                
                return Data(data={
                    "audio_base64": audio_base64,
                    "format": format_,
                    "voice": voice,
                    "speed": speed,
                    "size_bytes": len(response.content),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                })
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def generate_audio_base64(self) -> Message:
        """Generate audio and return only the base64 as text message."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Message(text="Error: No text provided for audio generation")

            api_key = self._get_api_key()
            voice = getattr(self, 'voice', 'alloy') or 'alloy'
            format_ = getattr(self, 'audio_format', 'mp3') or 'mp3'
            speed = getattr(self, 'speed', 1) or 1

            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "response_format": format_,
                "speed": float(speed)
            }

            self.status = f"Generating audio with voice '{voice}' in '{format_}' format at speed {speed}x..."
            self.log(f"Making TTS request with voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                audio_size_kb = len(response.content) / 1024
                
                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")
                
                return Message(text=audio_base64)
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                self.status = f"Error: {error_msg}"
                return Message(text=f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def generate_playground_audio(self) -> Message:
        """Generate HTML audio player code for the generated audio."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Message(text="Error: No text provided for audio generation")

            api_key = self._get_api_key()
            voice = getattr(self, 'voice', 'alloy') or 'alloy'
            format_ = getattr(self, 'audio_format', 'mp3') or 'mp3'
            speed = getattr(self, 'speed', 1) or 1

            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "response_format": format_,
                "speed": float(speed)
            }

            self.status = f"Generating audio with voice '{voice}' in '{format_}' format at speed {speed}x..."
            self.log(f"Making TTS request with voice: {voice}, format: {format_}, speed: {speed}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200 and response.content:
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                audio_size_kb = len(response.content) / 1024
                
                self.status = f"Audio generated successfully! Size: {audio_size_kb:.1f} KB"
                self.log(f"Audio generated successfully. Size: {len(response.content)} bytes")
                
                # Generate HTML audio player code
                html_code = f'<audio controls>\n  <source src="data:audio/{format_};base64,{audio_base64}" type="audio/{format_}">\n</audio>'
                
                return Message(text=html_code)
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                self.status = f"Error: {error_msg}"
                return Message(text=f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Error generating playground audio: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def generate_image(self) -> Data:
        """Generate image from text using OpenAI DALL-E API."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Data(data={"error": "No text provided for image generation"})

            api_key = self._get_api_key()
            model = getattr(self, 'image_model', 'dall-e-3') or 'dall-e-3'
            size = getattr(self, 'image_size', '1024x1024') or '1024x1024'
            n = getattr(self, 'num_images', 1) or 1

            client = OpenAI(api_key=api_key)

            self.status = f"Generating image using {model} model..."
            self.log(f"Making image generation request with model: {model}, size: {size}, count: {n}")

            response = client.images.generate(
                model=model,
                prompt=text,
                n=n,
                size=size
            )

            image_urls = [data.url for data in response.data]
            self.status = f"Generated {len(image_urls)} image(s) successfully!"
            self.log(f"Generated {len(image_urls)} images")

            # Se apenas uma imagem foi gerada, retornar a URL diretamente
            if n == 1 and len(image_urls) == 1:
                return Data(data={
                    "image_url": image_urls[0],
                    "model": model,
                    "size": size,
                    "count": n,
                    "prompt": text[:100] + "..." if len(text) > 100 else text,
                })
            else:
                return Data(data={
                    "image_urls": image_urls,
                    "model": model,
                    "size": size,
                    "count": n,
                    "prompt": text[:100] + "..." if len(text) > 100 else text,
                })

        except Exception as e:
            error_msg = f"Error generating image: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def generate_image_url(self) -> Message:
        """Generate image and return only the URL as text message."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Message(text="Error: No text provided for image generation")

            api_key = self._get_api_key()
            model = getattr(self, 'image_model', 'dall-e-3') or 'dall-e-3'
            size = getattr(self, 'image_size', '1024x1024') or '1024x1024'
            n = getattr(self, 'num_images', 1) or 1

            client = OpenAI(api_key=api_key)

            self.status = f"Generating image using {model} model..."
            self.log(f"Making image generation request with model: {model}, size: {size}, count: {n}")

            response = client.images.generate(
                model=model,
                prompt=text,
                n=n,
                size=size
            )

            # Return only the first image URL as text
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                self.status = f"Generated image URL successfully!"
                self.log(f"Generated image URL: {image_url}")
                
                return Message(text=image_url)
            else:
                error_msg = "No image URL generated"
                self.status = f"Error: {error_msg}"
                return Message(text=f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Error generating image URL: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def generate_playground_image(self) -> Message:
        """Generate markdown image code for the generated image (only for single image)."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Message(text="Error: No text provided for image generation")

            # Check if only one image is requested
            n = getattr(self, 'num_images', 1) or 1
            if n != 1:
                return Message(text="Playground Image output is only available when generating a single image (Number of Images = 1)")

            api_key = self._get_api_key()
            model = getattr(self, 'image_model', 'dall-e-3') or 'dall-e-3'
            size = getattr(self, 'image_size', '1024x1024') or '1024x1024'

            client = OpenAI(api_key=api_key)

            self.status = f"Generating image using {model} model..."
            self.log(f"Making image generation request with model: {model}, size: {size}, count: {n}")

            response = client.images.generate(
                model=model,
                prompt=text,
                n=n,
                size=size
            )

            # Return markdown image code for the first image
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                # Create a description from the prompt
                description = text[:50] + "..." if len(text) > 50 else text
                markdown_code = f"![{description}]({image_url})"
                
                self.status = f"Generated playground image markdown successfully!"
                self.log(f"Generated playground image markdown: {markdown_code}")
                
                return Message(text=markdown_code)
            else:
                error_msg = "No image URL generated"
                self.status = f"Error: {error_msg}"
                return Message(text=f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Error generating playground image: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def generate_video(self) -> Data:
        """Generate video from text (placeholder for future implementation)."""
        try:
            text = self._extract_text_from_input()
            if not text or not text.strip():
                return Data(data={"error": "No text provided for video generation"})

            # Placeholder for video generation
            # TODO: Implement video generation when OpenAI video API is available
            self.status = "Video generation not yet implemented"
            self.log("Video generation requested but not yet implemented")
            
            return Data(data={
                "error": "Video generation is not yet implemented. This feature will be available when OpenAI releases their video generation API.",
                "text": text[:100] + "..." if len(text) > 100 else text,
            })

        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})
