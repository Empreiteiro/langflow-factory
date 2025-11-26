import json
from typing import Any

from json_repair import repair_json

from langflow.custom.custom_component.component import Component
from langflow.io import MultilineInput, Output, TabInput
from langflow.schema.data import Data
from langflow.schema.dataframe import DataFrame
from langflow.schema.message import Message


class FlexibleInputComponent(Component):
    display_name = "Input"
    description = "Input component with Text, JSON, or DataFrame modes."
    icon = "type"
    name = "FlexibleInput"

    inputs = [
        TabInput(
            name="mode",
            display_name="Mode",
            options=["Text", "JSON", "DataFrame"],
            value="Text",
            info="Choose between Text mode (outputs Message), JSON mode (outputs Data), or DataFrame mode (outputs DataFrame).",
            real_time_refresh=True,
        ),
        MultilineInput(
            name="text_value",
            display_name="Input Text",
            info="Text to be passed as output when Mode is Text.",
            dynamic=True,
            show=True,
        ),
        MultilineInput(
            name="json_string",
            display_name="JSON String",
            info="Enter a valid JSON string to convert to a Data object when Mode is JSON.",
            dynamic=True,
            show=False,
        ),
        MultilineInput(
            name="data_list_json",
            display_name="Data List (JSON)",
            info="Enter a JSON array of objects to convert to DataFrame when Mode is DataFrame. Each object in the array will become a row in the DataFrame.",
            dynamic=True,
            show=False,
        ),
    ]

    # Outputs will be set dynamically by update_outputs
    outputs = []

    def update_build_config(self, build_config, field_value: Any, field_name: str | None = None):
        """Update input visibility based on selected mode."""
        if field_name == "mode" or field_name is None:
            # Get current mode from build_config or field_value
            if field_name == "mode":
                mode = field_value if isinstance(field_value, str) else "Text"
            else:
                # On initial load, get from build_config
                mode = build_config.get("mode", {}).get("value", "Text") if isinstance(build_config, dict) else getattr(build_config.mode, "value", "Text") if hasattr(build_config, "mode") else "Text"
            
            # Toggle visibility of inputs to match selected mode
            is_text = mode == "Text"
            is_json = mode == "JSON"
            is_dataframe = mode == "DataFrame"
            
            if "text_value" in build_config:
                if isinstance(build_config, dict):
                    build_config["text_value"]["show"] = is_text
                else:
                    build_config.text_value.show = is_text
            if "json_string" in build_config:
                if isinstance(build_config, dict):
                    build_config["json_string"]["show"] = is_json
                else:
                    build_config.json_string.show = is_json
            if "data_list_json" in build_config:
                if isinstance(build_config, dict):
                    build_config["data_list_json"]["show"] = is_dataframe
                else:
                    build_config.data_list_json.show = is_dataframe
        
        return build_config
    
    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any):
        """Dynamically expose only the relevant output based on mode."""
        if field_name == "mode" or field_name is None:
            # Get current mode
            if field_name == "mode":
                mode = field_value if isinstance(field_value, str) else "Text"
            else:
                # On initial load, try to get from frontend_node or use default
                try:
                    mode = frontend_node.get("data", {}).get("node", {}).get("template", {}).get("mode", {}).get("value", "Text")
                except (AttributeError, KeyError, TypeError):
                    mode = "Text"
                
                if not mode or mode not in ["Text", "JSON", "DataFrame"]:
                    mode = "Text"
            
            frontend_node["outputs"] = []
            if mode == "Text":
                frontend_node["outputs"].append(
                    Output(display_name="Text Output", name="text", method="text_output")
                )
            elif mode == "JSON":
                frontend_node["outputs"].append(
                    Output(display_name="Data Output", name="data", method="data_output")
                )
            else:  # DataFrame mode
                frontend_node["outputs"].append(
                    Output(display_name="DataFrame Output", name="dataframe", method="dataframe_output")
                )
        return frontend_node

    def text_output(self) -> Message:
        """Output text as Message when in Text mode."""
        # Get current mode
        current_mode = getattr(self, "mode", "Text")
        
        # If mode is not Text but text_output is called, return empty message
        # This should not happen if update_outputs works correctly, but handle gracefully
        if current_mode != "Text":
            return Message(text="")
        
        message = Message(
            text=self.text_value or "",
        )
        self.status = self.text_value or ""
        return message

    def data_output(self) -> Data | list[Data]:
        """Output JSON as Data when in JSON mode."""
        # Get current mode
        current_mode = getattr(self, "mode", "Text")
        
        # If mode is not JSON but data_output is called, return empty data
        # This should not happen if update_outputs works correctly, but handle gracefully
        if current_mode != "JSON":
            return Data(data={})
        
        if not self.json_string:
            raise ValueError("JSON string is required when mode is 'JSON'")

        try:
            # Try to parse the JSON string
            try:
                parsed_data = json.loads(self.json_string)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to repair the JSON string
                repaired_json_string = repair_json(self.json_string)
                parsed_data = json.loads(repaired_json_string)

            # Check if the parsed data is a list
            if isinstance(parsed_data, list):
                result = [Data(data=item) for item in parsed_data]
            else:
                result = Data(data=parsed_data)
            
            self.status = result
            return result

        except (json.JSONDecodeError, SyntaxError, ValueError) as e:
            error_message = f"Invalid JSON: {e}"
            self.status = error_message
            raise ValueError(error_message) from e

        except Exception as e:
            error_message = f"An error occurred: {e}"
            self.status = error_message
            raise ValueError(error_message) from e

    def dataframe_output(self) -> DataFrame:
        """Output DataFrame when in DataFrame mode."""
        # Get current mode
        current_mode = getattr(self, "mode", "Text")
        
        # If mode is not DataFrame but dataframe_output is called, return empty DataFrame
        # This should not happen if update_outputs works correctly, but handle gracefully
        if current_mode != "DataFrame":
            return DataFrame({})
        
        if not self.data_list_json:
            raise ValueError("Data list JSON string is required when mode is 'DataFrame'")
        
        try:
            # Parse the JSON string
            try:
                parsed_data = json.loads(self.data_list_json)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to repair the JSON string
                repaired_json_string = repair_json(self.data_list_json)
                parsed_data = json.loads(repaired_json_string)
            
            # Ensure parsed_data is a list
            if not isinstance(parsed_data, list):
                # If single object, wrap in list
                parsed_data = [parsed_data]
            
            if not parsed_data:
                raise ValueError("Data list cannot be empty")
            
            # Convert each item in the list to a Data object
            data_list = [Data(data=item) for item in parsed_data]
            
            # Convert to DataFrame
            result = DataFrame(data_list)
            return result
        
        except (json.JSONDecodeError, SyntaxError, ValueError) as e:
            error_message = f"Invalid JSON or error creating DataFrame: {e}"
            self.status = error_message
            raise ValueError(error_message) from e
        
        except Exception as e:
            error_message = f"Error creating DataFrame: {e}"
            self.status = error_message
            raise ValueError(error_message) from e

