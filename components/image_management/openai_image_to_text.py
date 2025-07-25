from langflow.custom import Component
from langflow.io import FileInput, SecretStrInput, Output
from langflow.schema import Data
from openai import OpenAI
import base64
import os

class ImageToTextComponent(Component):
    display_name = "Image to Text"
    description = "Uses OpenAI's API to describe an image or extract text from image."
    icon = "OpenAI"
    name = "ImageToTextComponent"
    field_order = ["image_file", "openai_api_key"]

    inputs = [
        FileInput(
            name="image_file",
            display_name="Image File",
            file_types=["png", "jpg", "jpeg", "webp"],  # No dots
            info="Upload the image to be processed.",
            required=True
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name="OpenAI API Key",
            info="Your OpenAI API key.",
            required=True
        )
    ]

    outputs = [
        Output(name="text_output", display_name="Text Output", method="text_output")
    ]

    def build(self):
        try:
            if isinstance(self.image_file, str):
                image_path = self.image_file
            elif hasattr(self.image_file, "path"):
                image_path = self.image_file.path
            else:
                raise ValueError("Invalid image_file input. Expected file path as string or file object with 'path' attribute.")

            with open(image_path, "rb") as f:
                image_data = f.read()

            base64_image = base64.b64encode(image_data).decode("utf-8")

            api_key = self.openai_api_key
            if hasattr(api_key, 'get_secret_value'):
                api_key = api_key.get_secret_value()

            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe the image or extract text if present."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )

            content = response.choices[0].message.content

            self.status = "Success"
            return Data(data={"text": content})

        except Exception as e:
            error_msg = f"Failed to process image: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def text_output(self) -> Data:
        return self.build()
