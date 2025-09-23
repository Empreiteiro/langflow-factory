import json
import re
from typing import Any, Dict, Union

from lfx.custom.custom_component.component import Component
from lfx.io import MultilineInput, Output, BoolInput
from lfx.schema.data import Data


class EnhancedWebhookComponent(Component):
    display_name = "Enhanced Webhook"
    documentation: str = "https://docs.langflow.org/components-data#enhanced-webhook"
    name = "EnhancedWebhook"
    icon = "webhook"

    inputs = [
        MultilineInput(
            name="data",
            display_name="Payload",
            info="Receives a payload from external systems via HTTP POST.",
            advanced=True,
        ),
        MultilineInput(
            name="curl",
            display_name="cURL",
            value="CURL_WEBHOOK",
            advanced=True,
            input_types=[],
        ),
        MultilineInput(
            name="endpoint",
            display_name="Endpoint",
            value="BACKEND_URL",
            advanced=False,
            copy_field=True,
            input_types=[],
        ),
        BoolInput(
            name="auto_parse_nested",
            display_name="Auto Parse Nested JSON",
            value=True,
            info="Automatically parse nested JSON strings in payload fields",
        ),
        BoolInput(
            name="flatten_nested_objects",
            display_name="Flatten Nested Objects",
            value=False,
            info="Flatten nested objects into dot notation keys",
        ),
    ]
    outputs = [
        Output(display_name="Data", name="output_data", method="build_data"),
    ]

    def _clean_json_string(self, json_str: str) -> str:
        """Clean and prepare JSON string for parsing."""
        # Remove extra quotes and fix common issues
        cleaned = json_str.strip()
        
        # Fix common newline issues
        cleaned = cleaned.replace('"\n"', '"\\n"')
        cleaned = cleaned.replace('"\r"', '"\\r"')
        cleaned = cleaned.replace('"\t"', '"\\t"')
        
        # Remove extra quotes at the beginning and end if they exist
        if cleaned.startswith('"') and cleaned.endswith('"'):
            # Check if it's a valid JSON string (not just a string containing JSON)
            try:
                # Try to parse as is first
                json.loads(cleaned)
                return cleaned
            except json.JSONDecodeError:
                # If it's a string containing JSON, remove the outer quotes
                cleaned = cleaned[1:-1]
        
        return cleaned

    def _parse_nested_json(self, obj: Any, auto_parse: bool = True) -> Any:
        """Recursively parse nested JSON strings in the object."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if isinstance(value, str) and auto_parse:
                    # Try to parse as JSON if it looks like JSON
                    if value.strip().startswith('{') and value.strip().endswith('}'):
                        try:
                            cleaned_value = self._clean_json_string(value)
                            parsed_value = json.loads(cleaned_value)
                            result[key] = self._parse_nested_json(parsed_value, auto_parse)
                        except (json.JSONDecodeError, ValueError):
                            result[key] = self._parse_nested_json(value, auto_parse)
                    elif value.strip().startswith('[') and value.strip().endswith(']'):
                        try:
                            cleaned_value = self._clean_json_string(value)
                            parsed_value = json.loads(cleaned_value)
                            result[key] = self._parse_nested_json(parsed_value, auto_parse)
                        except (json.JSONDecodeError, ValueError):
                            result[key] = self._parse_nested_json(value, auto_parse)
                    else:
                        result[key] = value
                else:
                    result[key] = self._parse_nested_json(value, auto_parse)
            return result
        elif isinstance(obj, list):
            return [self._parse_nested_json(item, auto_parse) for item in obj]
        else:
            return obj

    def _flatten_object(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        """Flatten nested objects using dot notation."""
        flattened = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    flattened.update(self._flatten_object(value, new_key))
                else:
                    flattened[new_key] = value
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
                if isinstance(item, (dict, list)):
                    flattened.update(self._flatten_object(item, new_key))
                else:
                    flattened[new_key] = item
        else:
            flattened[prefix] = obj
            
        return flattened

    def build_data(self) -> Data:
        message: str | Data = ""
        
        if not self.data:
            self.status = "No data provided."
            return Data(data={})
        
        try:
            # First, try to parse the raw data as JSON
            cleaned_data = self._clean_json_string(self.data)
            body = json.loads(cleaned_data or "{}")
            
            # Parse nested JSON strings if enabled
            if self.auto_parse_nested:
                body = self._parse_nested_json(body, self.auto_parse_nested)
            
            # Flatten the object if enabled
            if self.flatten_nested_objects:
                body = self._flatten_object(body)
            
            data = Data(data=body)
            message = data
            self.status = "Payload processed successfully."
            
        except json.JSONDecodeError as e:
            # If the main payload is not valid JSON, try to extract JSON from common patterns
            try:
                # Look for JSON patterns in the string
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                matches = re.findall(json_pattern, self.data)
                
                if matches:
                    # Try the longest match first
                    longest_match = max(matches, key=len)
                    cleaned_match = self._clean_json_string(longest_match)
                    body = json.loads(cleaned_match)
                    
                    # Parse nested JSON strings if enabled
                    if self.auto_parse_nested:
                        body = self._parse_nested_json(body, self.auto_parse_nested)
                    
                    # Flatten the object if enabled
                    if self.flatten_nested_objects:
                        body = self._flatten_object(body)
                    
                    data = Data(data=body)
                    message = data
                    self.status = f"Extracted JSON from payload. Original error: {str(e)}"
                else:
                    # Fallback to treating as raw data
                    body = {"raw_payload": self.data, "error": "Invalid JSON format"}
                    data = Data(data=body)
                    message = data
                    self.status = f"Invalid JSON payload. Treated as raw data. Error: {str(e)}"
                    
            except Exception as nested_error:
                # Final fallback
                body = {"raw_payload": self.data, "error": f"Failed to parse JSON: {str(e)}"}
                data = Data(data=body)
                message = data
                self.status = f"Failed to process payload: {str(nested_error)}"
        
        return data 
