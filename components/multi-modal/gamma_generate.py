from langflow.custom import Component
from langflow.io import (
    SecretStrInput,
    DropdownInput,
    SliderInput,
    BoolInput,
    MultilineInput,
    Output,
)
from langflow.field_typing.range_spec import RangeSpec
from langflow.schema import Data
import requests
import json


class GammaGenerateComponent(Component):
    display_name = "Gamma Generate"
    description = "Generates content using the Gamma API /v1/generate."
    icon = "mdi-creation"
    name = "GammaGenerateComponent"
    beta = False

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Gamma API key."
        ),
        MultilineInput(
            name="prompt",
            display_name="Prompt",
            required=True,
            info="Text to be sent for generation."
        ),
        DropdownInput(
            name="type",
            display_name="Generation Type",
            info="Defines the type of presentation.",
            options=["web", "presentation"],
            value="web",
        ),
        DropdownInput(
            name="aspect_ratio",
            display_name="Aspect Ratio",
            info="Aspect ratio for the presentation (e.g., 16:9, 4:3, 1:1).",
            options=["16:9", "4:3", "1:1"],
            value="16:9",
        ),
        SliderInput(
            name="creativity",
            display_name="Creativity",
            info="Creativity value between 0 and 1.",
            value=0.5,
            range_spec=RangeSpec(min=0.0, max=1.0, step=0.1),
        ),
        BoolInput(
            name="include_images",
            display_name="Include Images",
            value=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Result",
            method="generate_output",
        )
    ]

    field_order = [
        "api_key",
        "prompt",
        "type",
        "aspect_ratio",
        "creativity",
        "include_images",
    ]

    def build(self):
        """Executes the Gamma API call and saves the result in state."""
        url = "https://api.gamma.app/v1/generate"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": self.prompt,
            "type": self.type,
            "aspect_ratio": self.aspect_ratio,
            "creativity": self.creativity,
            "include_images": self.include_images,
        }

        try:
            self.log(f"Sending request to Gamma: {repr(payload)}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code != 200:
                msg = f"Gamma API error ({response.status_code}): {response.text}"
                self.status = msg
                self.update_state("gamma_result", {"error": msg})
                return

            data = response.json()
            self.update_state("gamma_result", data)
            self.status = "Generation completed."

        except Exception as e:
            msg = f"Error calling Gamma API: {e!s}"
            self.status = msg
            self.update_state("gamma_result", {"error": msg})

    def generate_output(self) -> Data:
        """Returns the result stored in state."""
        result = self.get_state("gamma_result")

        if not result:
            return Data(data={"error": "No result found."})

        return Data(data=result)
