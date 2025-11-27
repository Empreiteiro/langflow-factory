from langflow.custom import Component
from langflow.io import (
    SecretStrInput,
    DropdownInput,
    BoolInput,
    MultilineInput,
    StrInput,
    MessageTextInput,
    DictInput,
    Output,
)
from langflow.schema import Data
import requests
import json
from typing import Any, Optional


class GammaGenerateFromTemplateComponent(Component):
    display_name = "Gamma Generate From Template"
    description = "Generates content from a Gamma template using the API /v1.0/generations/from-template."
    icon = "custom"
    name = "GammaGenerateFromTemplateComponent"
    beta = False

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Gamma API key (X-API-KEY header)."
        ),
        StrInput(
            name="gamma_id",
            display_name="Gamma ID",
            required=True,
            info="The Gamma ID of the template to use (e.g., g_abcdef123456ghi)."
        ),
        MultilineInput(
            name="prompt",
            display_name="Prompt",
            required=True,
            info="Text prompt to rework the template (e.g., 'Rework this pitch deck for a non-technical audience.')."
        ),
        StrInput(
            name="theme_id",
            display_name="Theme ID",
            required=False,
            info="Theme ID for the presentation (e.g., 'Chisel').",
            advanced=True,
        ),
        MessageTextInput(
            name="folder_ids",
            display_name="Folder IDs",
            required=False,
            info="List of folder IDs where the generated content should be saved.",
            is_list=True,
            advanced=True,
        ),
        DropdownInput(
            name="export_as",
            display_name="Export As",
            required=False,
            info="Export format for the generated content.",
            options=["pdf", "pptx", "web"],
            value="pdf",
            advanced=True,
        ),
        DictInput(
            name="image_options",
            display_name="Image Options",
            required=False,
            info="Options for image generation. Example: {'model': 'imagen-4-pro', 'style': 'photorealistic'}",
            value={"model": "imagen-4-pro", "style": "photorealistic"},
            advanced=True,
        ),
        DictInput(
            name="sharing_options",
            display_name="Sharing Options",
            required=False,
            info="Sharing and access options. Example: {'workspaceAccess': 'view', 'externalAccess': 'noAccess'}",
            value={},
            advanced=True,
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
        "gamma_id",
        "prompt",
        "theme_id",
        "folder_ids",
        "export_as",
        "image_options",
        "sharing_options",
    ]

    def build(self):
        """Executes the Gamma API call and saves the result in state."""
        url = "https://public-api.gamma.app/v1.0/generations/from-template"

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        # Build payload
        payload: dict[str, Any] = {
            "gammaId": self.gamma_id,
            "prompt": self.prompt,
        }

        # Add optional fields if provided
        if hasattr(self, "theme_id") and self.theme_id:
            payload["themeId"] = self.theme_id

        if hasattr(self, "folder_ids") and self.folder_ids:
            # Process folder_ids - it might be a list or need to be parsed
            folder_ids_list = self._parse_folder_ids(self.folder_ids)
            if folder_ids_list:
                payload["folderIds"] = folder_ids_list

        if hasattr(self, "export_as") and self.export_as:
            payload["exportAs"] = self.export_as

        if hasattr(self, "image_options") and self.image_options:
            # Ensure image_options is a dict
            image_opts = self.image_options
            if isinstance(image_opts, dict):
                payload["imageOptions"] = image_opts
            elif isinstance(image_opts, str):
                try:
                    payload["imageOptions"] = json.loads(image_opts)
                except json.JSONDecodeError:
                    self.log(f"Warning: Could not parse image_options as JSON: {image_opts}")

        if hasattr(self, "sharing_options") and self.sharing_options:
            # Ensure sharing_options is a dict
            sharing_opts = self.sharing_options
            if isinstance(sharing_opts, dict):
                payload["sharingOptions"] = sharing_opts
            elif isinstance(sharing_opts, str):
                try:
                    payload["sharingOptions"] = json.loads(sharing_opts)
                except json.JSONDecodeError:
                    self.log(f"Warning: Could not parse sharing_options as JSON: {sharing_opts}")

        try:
            self.log(f"Sending request to Gamma API: {url}")
            self.log(f"Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, json=payload, timeout=120)

            if response.status_code != 200:
                msg = f"Gamma API error ({response.status_code}): {response.text}"
                self.status = msg
                self.update_state("gamma_result", {"error": msg})
                return

            data = response.json()
            self.update_state("gamma_result", data)
            self.status = "Generation from template completed."

        except Exception as e:
            msg = f"Error calling Gamma API: {e!s}"
            self.status = msg
            self.update_state("gamma_result", {"error": msg})
            self.log(msg)

    def _parse_folder_ids(self, folder_ids_input: Any) -> list[str]:
        """Parse folder IDs from various input formats."""
        if not folder_ids_input:
            return []

        if isinstance(folder_ids_input, list):
            folder_ids = []
            for item in folder_ids_input:
                if isinstance(item, str) and item.strip():
                    folder_ids.append(item.strip())
                elif hasattr(item, "text"):
                    text = getattr(item, "text", "") or ""
                    if text.strip():
                        folder_ids.append(text.strip())
                else:
                    folder_ids.append(str(item).strip())
            return folder_ids

        if isinstance(folder_ids_input, str):
            # Try to parse as JSON array or comma-separated
            try:
                parsed = json.loads(folder_ids_input)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
            except json.JSONDecodeError:
                # Treat as comma-separated string
                return [item.strip() for item in folder_ids_input.split(",") if item.strip()]

        return [str(folder_ids_input).strip()]

    def generate_output(self) -> Data:
        """Returns the result stored in state."""
        result = self.get_state("gamma_result")

        if not result:
            return Data(data={"error": "No result found."})

        return Data(data=result)

