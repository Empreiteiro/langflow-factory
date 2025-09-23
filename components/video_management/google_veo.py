import time
from lfx.custom import Component
from lfx.io import StrInput, MultilineInput, SecretStrInput, Output, DropdownInput
from lfx.schema import Data, Message

from google import genai
from google.genai import types

class GoogleVeoVideoGenerator(Component):
    display_name = "Google Video Generator"
    description = "Generate videos using the official Google Veo."
    icon = "Google"
    name = "GoogleVeo2VideoGenerator"

    field_order = ["api_key", "model", "prompt", "aspect_ratio", "allow_people"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Your API key for authentication with the Gemini SDK.",
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Veo model to use for video generation",
            options=[
                "veo-3.0-generate-preview",  # Latest Veo 3.0 model
                "veo-2.0-generate-001",  # Veo 2.0 model (requires GCP billing)
                "models/veo-2.0-generate-001",  # Full format for Veo 2.0
            ],
            value="veo-2.0-generate-001",  # Default to latest Veo 3.0
        ),
        MultilineInput(
            name="prompt",
            display_name="Prompt",
            info="Text prompt to generate the video.",
            required=True,
        ),
        DropdownInput(
            name="aspect_ratio",
            display_name="Aspect Ratio",
            info="Video format ratio",
            options=[
                "16:9",  # Widescreen
                "9:16",  # Portrait/Vertical
            ],
            value="16:9",
        ),
        DropdownInput(
            name="allow_people",
            display_name="Allow People",
            info="Whether to allow people generation in videos",
            options=[
                "dont_allow",   # Don't allow people
                "allow_adult",  # Allow adult people
            ],
            value="dont_allow",
        ),
    ]

    outputs = [
        Output(name="video_data", display_name="Video Data", method="build"),
        Output(name="playground_video", display_name="Playground Video", method="generate_playground_video"),
    ]

    def build(self) -> Data:
        try:
            # Create client with API key directly (correct way for Google GenAI SDK)
            client = genai.Client(api_key=self.api_key)

            # Generate video using the selected model
            operation = client.models.generate_videos(
                model=self.model,  # Use selected model instead of hardcoded
                prompt=self.prompt,
                config=types.GenerateVideosConfig(
                    person_generation=self.allow_people,
                    aspect_ratio=self.aspect_ratio,
                ),
            )

            self.status = f"Waiting for video generation completion using {self.model}..."
            
            # Poll for completion with proper interval (20 seconds as per documentation)
            while not operation.done:
                time.sleep(20)
                operation = client.operations.get(operation)

            # Process generated videos according to documentation
            video_urls = []
            video_data = []
            
            for n, generated_video in enumerate(operation.response.generated_videos):
                if hasattr(generated_video, 'video') and generated_video.video:
                    video_info = {
                        "video_id": n,
                        "video_object": generated_video.video
                    }
                    
                    # Add URI if available (needs API key appended for download)
                    if hasattr(generated_video.video, 'uri'):
                        video_url = f"{generated_video.video.uri}&key={self.api_key}"
                        video_info["video_uri"] = video_url
                        video_urls.append(video_url)
                    
                    video_data.append(video_info)

            if not video_data:
                raise ValueError("No video was generated.")

            self.status = f"Video(s) generated successfully using {self.model}. Total: {len(video_data)}"
            
            # Return the first video URL as main output, with detailed data available
            primary_video_url = video_urls[0] if video_urls else None
            
            return Data(data={
                "video_url": primary_video_url,  # Direct link to first video
                "video_urls": video_urls,        # List of all links
                "video_count": len(video_data),
                "videos": video_data,            # Complete data
                "model_used": self.model,        # Model used
                "prompt_used": self.prompt,
                "aspect_ratio": self.aspect_ratio
            })

        except Exception as e:
            error_message = str(e)
            self.status = f"Error with model {self.model}: {error_message}"
            
            # Provide helpful error info
            return Data(data={
                "error": error_message,
                "model_attempted": self.model,
                "video_count": 0,
                "suggestion": "Try using veo-3.0-generate-001 for the latest model, or check your API key and billing setup"
            })

    def generate_playground_video(self) -> Message:
        """Generate HTML video player code for the generated video."""
        try:
            # First, generate the video using the build method
            video_result = self.build()
            
            # Check if video generation was successful
            if hasattr(video_result, 'data') and isinstance(video_result.data, dict):
                if 'error' in video_result.data:
                    return Message(text=f"Error: {video_result.data['error']}")
                
                # Get the primary video URL
                video_url = video_result.data.get('video_url')
                if not video_url:
                    return Message(text="Error: No video URL generated")
                
                # Determine aspect ratio for dimensions
                aspect_ratio = self.aspect_ratio
                if aspect_ratio == "16:9":
                    width, height = 640, 360
                elif aspect_ratio == "9:16":
                    width, height = 360, 640
                else:
                    width, height = 640, 360  # Default to 16:9
                
                # Generate HTML video player code
                html_code = f'<video width="{width}" height="{height}" controls>\n  <source src="{video_url}">\n</video>'
                
                self.status = f"Generated playground video HTML for {aspect_ratio} aspect ratio"
                return Message(text=html_code)
            else:
                return Message(text="Error: Invalid video generation result")
                
        except Exception as e:
            error_msg = f"Error generating playground video: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")
