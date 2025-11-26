from langflow.custom import Component
from langflow.io import StrInput, IntInput, SecretStrInput, DropdownInput, Output
from langflow.schema import Data
import openai

class DalleImageGenerator(Component):
    display_name = "DALL·E"
    description = "Generates an image using OpenAI's DALL·E models based on a text prompt."
    icon = "OpenAI"
    name = "DalleImageGenerator"

    inputs = [
        MessageInput(
            name="prompt",
            display_name="Prompt",
            info="The text prompt describing the image you want to generate.",
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            options=["dall-e-2", "dall-e-3"],
            value="dall-e-3",
            info="The DALL·E model version to use.",
        ),
        IntInput(
            name="n",
            display_name="Number of Images",
            value=1,
            info="Number of images to generate.",
        ),
        StrInput(
            name="size",
            display_name="Image Size",
            value="1024x1024",
            info="Size of the generated image. Example: 256x256, 512x512, 1024x1024.",
        ),
        SecretStrInput(
            name="api_key",
            display_name="OpenAI API Key",
            info="Your OpenAI API key.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="generated_images", display_name="Generated Images", method="generate_images"),
    ]

    field_order = ["prompt", "model", "n", "size", "api_key"]

    def generate_images(self) -> Data:
        try:
            client = openai.OpenAI(api_key=self.api_key)

            response = client.images.generate(
                model=self.model,
                prompt=self.prompt,
                n=self.n,
                size=self.size
            )

            image_urls = [data.url for data in response.data]
            self.log(f"Generated {len(image_urls)} images.")

            return Data(data={"image_urls": image_urls})

        except Exception as e:
            error_message = f"Error generating images: {str(e)}"
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})