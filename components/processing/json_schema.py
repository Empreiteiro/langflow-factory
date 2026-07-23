import json
from typing import Any

from pydantic import BaseModel
from trustcall import create_extractor

from lfx.base.models.chat_result import get_chat_result
from lfx.custom.custom_component.component import Component
from lfx.io import (
    HandleInput,
    MessageTextInput,
    MultilineInput,
    Output,
)
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame

DEFAULT_JSON_SCHEMA = """{
  "title": "Person",
  "description": "A single person extracted from the text.",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "The person's full name."
    },
    "age": {
      "type": "integer",
      "description": "The person's age in years."
    },
    "role": {
      "type": "string",
      "description": "The person's role.",
      "enum": ["admin", "editor", "viewer"]
    },
    "tags": {
      "type": "array",
      "description": "Zero or more free-form tags.",
      "items": {"type": "string"}
    }
  },
  "required": ["name"]
}"""


class JSONSchemaComponent(Component):
    display_name = "JSON Schema"
    description = (
        "Uses an LLM to generate data that conforms to a user-provided JSON Schema. "
        "Like Structured Output, but the schema is written directly as JSON, so each key "
        "can constrain its type, allowed values (enum), nesting and whether it is required."
    )
    documentation: str = "https://json-schema.org/understanding-json-schema/"
    name = "JSONSchema"
    icon = "braces"

    inputs = [
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="The language model used to generate the schema-conforming output.",
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="input_value",
            display_name="Input Message",
            info="The input message the model reads to produce the output.",
            tool_mode=True,
            required=True,
        ),
        MultilineInput(
            name="json_schema",
            display_name="JSON Schema",
            info=(
                "A valid JSON Schema (draft 2020-12 compatible) describing the desired output. "
                "The top-level type should be 'object' (or 'array' of objects). Use 'enum' to restrict "
                "a key to a set of values, 'required' to make keys mandatory, and nested 'properties' "
                "for nested objects. If a plain example object is provided instead of a schema, a schema "
                "is inferred from it."
            ),
            value=DEFAULT_JSON_SCHEMA,
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="Format Instructions",
            info="Instructions that tell the model how to fill the schema.",
            value=(
                "You are an AI that extracts and generates data conforming to a JSON Schema. "
                "Populate every required field and respect each field's type and allowed values (enum). "
                "When a value is missing or ambiguous in the input, choose the most reasonable value that "
                "still satisfies the schema; use null only for fields that are not required. "
                "Never invent keys that are not in the schema. Always return valid data in the expected format."
            ),
            required=True,
            advanced=True,
        ),
        MessageTextInput(
            name="schema_name",
            display_name="Schema Name",
            info="Optional name for the schema. Defaults to the schema's 'title' or 'OutputModel'.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="structured_output",
            display_name="Structured Output",
            method="build_structured_output",
        ),
        Output(
            name="dataframe_output",
            display_name="DataFrame",
            method="build_structured_dataframe",
        ),
    ]

    # Keys that signal the provided JSON is already a schema rather than an example instance.
    _SCHEMA_MARKERS = ("type", "properties", "$schema", "items", "$ref", "anyOf", "allOf", "oneOf", "enum")

    def _parse_json_schema(self) -> dict[str, Any]:
        """Parse the JSON Schema input into a dict, repairing minor JSON errors if needed."""
        raw = (self.json_schema or "").strip()
        if not raw:
            msg = "JSON Schema cannot be empty."
            raise ValueError(msg)
        try:
            schema = json.loads(raw)
        except json.JSONDecodeError:
            try:
                from json_repair import repair_json

                schema = json.loads(repair_json(raw))
            except Exception as exc:  # noqa: BLE001
                msg = f"Could not parse JSON Schema: {exc}"
                raise ValueError(msg) from exc
        if not isinstance(schema, dict):
            msg = "JSON Schema must be a JSON object."
            raise ValueError(msg)
        return schema

    def _looks_like_schema(self, schema: dict[str, Any]) -> bool:
        return any(marker in schema for marker in self._SCHEMA_MARKERS)

    def _infer_type(self, value: Any) -> dict[str, Any]:
        """Infer a minimal JSON Schema fragment from an example value."""
        if isinstance(value, bool):
            return {"type": "boolean"}
        if isinstance(value, int):
            return {"type": "integer"}
        if isinstance(value, float):
            return {"type": "number"}
        if isinstance(value, dict):
            return {
                "type": "object",
                "properties": {k: self._infer_type(v) for k, v in value.items()},
            }
        if isinstance(value, list):
            items = self._infer_type(value[0]) if value else {"type": "string"}
            return {"type": "array", "items": items}
        return {"type": "string"}

    def _infer_schema_from_example(self, example: dict[str, Any]) -> dict[str, Any]:
        """Build an object schema from a plain example object so the component stays forgiving."""
        self.log("Provided JSON looks like an example, not a schema. Inferring a schema from it.")
        return {
            "title": "OutputModel",
            "type": "object",
            "properties": {k: self._infer_type(v) for k, v in example.items()},
        }

    def _build_tool_schema(self, schema: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
        """Return (tool_dict, schema_name, wrapped_as_list).

        A top-level array schema is wrapped in an object under the "items" key, because tool
        parameters must be an object. `wrapped_as_list` tells the caller to unwrap the result.
        """
        if not self._looks_like_schema(schema):
            schema = self._infer_schema_from_example(schema)

        schema_name = (self.schema_name or schema.get("title") or "OutputModel").strip() or "OutputModel"
        description = schema.get("description", f"Output conforming to {schema_name}.")

        wrapped_as_list = schema.get("type") == "array"
        if wrapped_as_list:
            parameters = {
                "type": "object",
                "properties": {"items": schema},
                "required": ["items"],
            }
        else:
            parameters = schema

        tool = {"name": schema_name, "description": description, "parameters": parameters}
        return tool, schema_name, wrapped_as_list

    def _run_extraction(self) -> Any:
        """Run the LLM against the schema and return a dict or a list of dicts."""
        if not hasattr(self.llm, "with_structured_output"):
            msg = "Language model does not support structured output."
            raise TypeError(msg)

        schema = self._parse_json_schema()
        tool, schema_name, wrapped_as_list = self._build_tool_schema(schema)

        try:
            extractor = create_extractor(self.llm, tools=[tool], tool_choice=schema_name)
        except NotImplementedError as exc:
            msg = f"{self.llm.__class__.__name__} does not support structured output."
            raise TypeError(msg) from exc

        config_dict = {
            "display_name": self.display_name,
            "get_project_name": self.get_project_name,
            "get_langchain_callbacks": self.get_langchain_callbacks,
        }
        result = get_chat_result(
            runnable=extractor,
            system_message=self.system_prompt,
            input_value=self.input_value,
            config=config_dict,
        )

        if not isinstance(result, dict):
            return result

        responses = result.get("responses", [])
        if not responses:
            msg = "The model returned no output for the provided schema."
            raise ValueError(msg)

        first_response = responses[0]
        data = first_response.model_dump() if isinstance(first_response, BaseModel) else first_response

        if wrapped_as_list and isinstance(data, dict):
            return data.get("items", [])
        return data

    def build_structured_output(self) -> Data:
        output = self._run_extraction()
        if isinstance(output, list):
            if not output:
                msg = "No structured output returned."
                raise ValueError(msg)
            if len(output) == 1 and isinstance(output[0], dict):
                result = Data(data=output[0])
            else:
                result = Data(data={"results": output})
        elif isinstance(output, dict):
            result = Data(data=output)
        else:
            result = Data(data={"result": output})
        self.status = result
        return result

    def build_structured_dataframe(self) -> DataFrame:
        output = self._run_extraction()
        if isinstance(output, list):
            if not output:
                msg = "No structured output returned."
                raise ValueError(msg)
            data_list = [Data(data=item) if isinstance(item, dict) else Data(data={"value": item}) for item in output]
        elif isinstance(output, dict):
            data_list = [Data(data=output)]
        else:
            data_list = [Data(data={"value": output})]
        return DataFrame(data_list)
