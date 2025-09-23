from langflow.base.prompts.api_utils import process_prompt_template
from langflow.custom import Component
from langflow.inputs.inputs import DefaultPromptField
from langflow.io import MessageTextInput, Output, PromptInput, StrInput, DataInput
from langflow.schema.message import Message
from langflow.template.utils import update_template_values
import json


class cURLBuilder(Component):
    display_name: str = "cURL Builder"
    description: str = "Build cURL commands with dynamic variables in URL, headers, and body."
    icon = "prompts"
    trace_type = "prompt"
    name = "cURLBuilder"

    inputs = [
        StrInput(
            name="url",
            display_name="URL",
            required=True,
            info="The target URL for the API request. Use {variable} for dynamic values."
        ),
        PromptInput(
            name="template", 
            display_name="Body"
        ),
        MessageTextInput(
            name="tool_placeholder",
            display_name="Tool Placeholder",
            tool_mode=True,
            advanced=True,
            info="A placeholder input for tool mode.",
        ),

        MessageTextInput(
            name="headers",
            display_name="Headers",
            info="Enter one or more headers in 'Key: Value' format.",
            is_list=True,
        ),
    ]

    outputs = [
        Output(display_name="cURL", name="curl", method="build_curl"),
    ]

    def build_curl(self) -> Message:
        try:
            # Use the template system to get the processed template
            prompt = Message.from_template(**self._attributes)
            data = prompt.text
            
            # Handle different data types
            if hasattr(data, "data"):
                data = data.data
            elif hasattr(data, "text"):
                data = data.text
            elif isinstance(data, str):
                data = data
            else:
                data = str(data)

            # Try to parse as JSON if it's a string
            if isinstance(data, str):
                data = data.strip()
                
                # Check if it looks like a JSON fragment (key-value pairs)
                if self._is_json_fragment(data):
                    # Convert fragment to proper JSON
                    json_body = "{" + data + "}"
                    return self._build_curl_command(json_body)
                
                # Try to parse as complete JSON
                try:
                    if data.startswith('{') or data.startswith('['):
                        data = json.loads(data)
                    else:
                        # If it's not JSON, treat as plain text
                        json_body = json.dumps({"content": data}, ensure_ascii=False)
                        return self._build_curl_command(json_body)
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as plain text
                    json_body = json.dumps({"content": data}, ensure_ascii=False)
                    return self._build_curl_command(json_body)

            # Handle dictionary data
            if isinstance(data, dict):
                results = data.get("results")
                if results and isinstance(results, list) and results:
                    json_body = json.dumps(results[0], ensure_ascii=False)
                else:
                    # Use the entire data if no results key
                    json_body = json.dumps(data, ensure_ascii=False)
            else:
                # Fallback for other data types
                json_body = json.dumps({"content": str(data)}, ensure_ascii=False)

            return self._build_curl_command(json_body)

        except Exception as e:
            self.status = f"Error: {str(e)}"
            return Message(text=f"Error: {str(e)}")

    def _is_json_fragment(self, text: str) -> bool:
        """Check if the text looks like a JSON fragment (key-value pairs without braces)"""
        import re
        
        # Pattern to match key-value pairs like "key":"value" or "key": "value"
        pattern = r'^\s*"[^"]+"\s*:\s*"[^"]*"(?:\s*,\s*"[^"]+"\s*:\s*"[^"]*")*\s*$'
        return bool(re.match(pattern, text))

    def _build_curl_command(self, json_body: str) -> Message:
        """Helper method to build the cURL command"""
        curl_parts = [f"curl -X POST \"{self.url.strip()}\""]

        if self.headers:
            for line in self.headers:
                if ":" in line:
                    key, value = line.split(":", 1)
                    curl_parts.append(f"-H \"{key.strip()}: {value.strip()}\"")

        curl_parts.append(f"-d '{json_body}'")

        curl_command = " \\\n  ".join(curl_parts)
        self.status = f"Generated cURL command for {self.url}"
        return Message(text=curl_command)

    def _update_template(self, frontend_node: dict):
        prompt_template = frontend_node["template"]["template"]["value"]
        custom_fields = frontend_node["custom_fields"]
        frontend_node_template = frontend_node["template"]
        _ = process_prompt_template(
            template=prompt_template,
            name="template",
            custom_fields=custom_fields,
            frontend_node_template=frontend_node_template,
        )
        return frontend_node

    async def update_frontend_node(self, new_frontend_node: dict, current_frontend_node: dict):
        """This function is called after the code validation is done."""
        frontend_node = await super().update_frontend_node(new_frontend_node, current_frontend_node)
        template = frontend_node["template"]["template"]["value"]
        # Kept it duplicated for backwards compatibility
        _ = process_prompt_template(
            template=template,
            name="template",
            custom_fields=frontend_node["custom_fields"],
            frontend_node_template=frontend_node["template"],
        )
        # Now that template is updated, we need to grab any values that were set in the current_frontend_node
        # and update the frontend_node with those values
        update_template_values(new_template=frontend_node, previous_template=current_frontend_node["template"])
        return frontend_node

    def _get_fallback_input(self, **kwargs):
        return DefaultPromptField(**kwargs) 