import json
from typing import Any

from pydantic import BaseModel
from trustcall import create_extractor

from lfx.base.models.chat_result import get_chat_result
from lfx.base.models.unified_models import (
    get_llm,
    handle_model_input_update,
)
from lfx.custom.custom_component.component import Component
from lfx.io import (
    IntInput,
    MessageTextInput,
    ModelInput,
    MultilineInput,
    Output,
    SecretStrInput,
)
from lfx.schema.data import Data

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

MAX_REPORTED_ERRORS = 10


class JSONSchemaComponent(Component):
    display_name = "JSON Schema"
    description = "Uses an LLM to generate data that conforms to a JSON Schema."
    documentation: str = "https://json-schema.org/understanding-json-schema/"
    name = "JSONSchema"
    icon = "braces"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._extraction_result: tuple[Any, list[str], int] | None = None
        self._excluded_outputs: set[str] = set()

    inputs = [
        ModelInput(
            name="model",
            display_name="Language Model",
            info="Select your model provider",
            real_time_refresh=True,
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Overrides global provider settings. Leave blank to use your pre-configured API Key.",
            real_time_refresh=True,
            advanced=True,
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
        IntInput(
            name="max_retries",
            display_name="Max Retries",
            info=(
                "How many extra attempts to make when the output does not satisfy the schema. "
                "Each retry sends the validation errors back to the model. "
                "Set to 0 to route the first invalid output straight to the Invalid output."
            ),
            value=1,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Valid",
            name="valid_output",
            method="build_valid_output",
            group_outputs=True,
        ),
        Output(
            display_name="Invalid",
            name="invalid_output",
            method="build_invalid_output",
            group_outputs=True,
        ),
    ]

    # Keys that signal the provided JSON is already a schema rather than an example instance.
    _SCHEMA_MARKERS = ("type", "properties", "$schema", "items", "$ref", "anyOf", "allOf", "oneOf", "enum")

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        """Dynamically update build config with user-filtered model options."""
        return handle_model_input_update(self, build_config, field_value, field_name)

    def _pre_run_setup(self) -> None:
        """Reset per-run state before each build so every execution re-extracts and re-validates."""
        self._extraction_result = None
        self._excluded_outputs = set()

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
        if not self._looks_like_schema(schema):
            schema = self._infer_schema_from_example(schema)
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

    def _run_extraction(
        self, llm, tool: dict[str, Any], schema_name: str, *, wrapped_as_list: bool, prompt: str
    ) -> Any:
        """Run the LLM against the schema and return a dict or a list of dicts."""
        try:
            extractor = create_extractor(llm, tools=[tool], tool_choice=schema_name)
        except NotImplementedError as exc:
            msg = f"{llm.__class__.__name__} does not support structured output."
            raise TypeError(msg) from exc

        config_dict = {
            "display_name": self.display_name,
            "get_project_name": self.get_project_name,
            "get_langchain_callbacks": self.get_langchain_callbacks,
        }
        result = get_chat_result(
            runnable=extractor,
            system_message=prompt,
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

    def _validate_payload(self, payload: Any, parameters: dict[str, Any], *, wrapped_as_list: bool) -> list[str]:
        """Return a list of human-readable schema violations. An empty list means the payload is valid."""
        target = {"items": payload} if wrapped_as_list else payload

        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            return self._validate_with_pydantic(target, parameters, wrapped_as_list=wrapped_as_list)

        try:
            validator = Draft202012Validator(parameters)
            errors = list(validator.iter_errors(target))
        except Exception as exc:  # noqa: BLE001
            msg = f"The provided JSON Schema is not a valid schema: {exc}"
            raise ValueError(msg) from exc

        messages = [
            f"{self._error_path(error.absolute_path, wrapped_as_list=wrapped_as_list)}: {error.message}"
            for error in errors
        ]
        return self._truncate_errors(messages)

    def _validate_with_pydantic(self, target: Any, parameters: dict[str, Any], *, wrapped_as_list: bool) -> list[str]:
        """Fallback validation via dydantic, the schema-to-pydantic library trustcall already depends on.

        Used only when `jsonschema` is not installed. It is best-effort: pydantic coerces some
        scalars and dydantic does not enforce every JSON Schema keyword, so it catches missing
        required fields and wrong types but can let subtler constraints through.
        """
        from dydantic import create_model_from_schema
        from pydantic import ValidationError

        try:
            model = create_model_from_schema(parameters)
        except Exception as exc:  # noqa: BLE001
            msg = f"The provided JSON Schema is not a valid schema: {exc}"
            raise ValueError(msg) from exc

        try:
            model.model_validate(target)
        except ValidationError as exc:
            messages = [
                f"{self._error_path(error['loc'], wrapped_as_list=wrapped_as_list)}: {error['msg']}"
                for error in exc.errors()
            ]
            return self._truncate_errors(messages)
        return []

    @staticmethod
    def _error_path(path, *, wrapped_as_list: bool) -> str:
        """Render the location of a violation, hiding the internal "items" wrapper used for arrays."""
        parts = [str(part) for part in path]
        if wrapped_as_list and parts and parts[0] == "items":
            parts = parts[1:]
        return "/".join(parts) or "<root>"

    @staticmethod
    def _truncate_errors(messages: list[str]) -> list[str]:
        if len(messages) <= MAX_REPORTED_ERRORS:
            return messages
        hidden = len(messages) - MAX_REPORTED_ERRORS
        return [*messages[:MAX_REPORTED_ERRORS], f"... and {hidden} more validation error(s)."]

    def _extract_and_validate(self) -> tuple[Any, list[str], int]:
        """Extract, validate and retry with the validation errors fed back into the prompt.

        Returns (payload, errors, attempts). The LLM is only called once per component run, no
        matter how many outputs are connected, because the result is cached.
        """
        if self._extraction_result is not None:
            return self._extraction_result

        llm = get_llm(model=self.model, user_id=self.user_id, api_key=self.api_key)
        if not hasattr(llm, "with_structured_output"):
            msg = "Language model does not support structured output."
            raise TypeError(msg)

        schema = self._parse_json_schema()
        tool, schema_name, wrapped_as_list = self._build_tool_schema(schema)
        parameters = tool["parameters"]

        attempts = max(int(getattr(self, "max_retries", 1) or 0), 0) + 1
        base_prompt = self.system_prompt
        prompt = base_prompt
        payload: Any = None
        errors: list[str] = []
        extraction_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                payload = self._run_extraction(llm, tool, schema_name, wrapped_as_list=wrapped_as_list, prompt=prompt)
            except TypeError:
                raise
            except Exception as exc:  # noqa: BLE001
                # Keep trying: a transient failure may still succeed on the next attempt.
                extraction_error = exc
                self.log(f"Attempt {attempt}/{attempts} failed to produce output: {exc}")
                continue

            extraction_error = None
            errors = self._validate_payload(payload, parameters, wrapped_as_list=wrapped_as_list)
            if not errors:
                self._extraction_result = (payload, [], attempt)
                return self._extraction_result

            self.log(f"Attempt {attempt}/{attempts} produced output that violates the schema: {errors}")
            violations = "\n".join(f"- {error}" for error in errors)
            prompt = (
                f"{base_prompt}\n\n"
                f"A previous attempt returned this output:\n{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
                f"It was rejected because it violates the schema:\n{violations}\n\n"
                f"Return a corrected output that fixes every violation above."
            )

        if extraction_error is not None:
            # Never produced anything: this is a real failure, not a schema violation.
            msg = f"Could not get an output from the model after {attempts} attempt(s): {extraction_error}"
            raise ValueError(msg) from extraction_error

        self._extraction_result = (payload, errors, attempts)
        return self._extraction_result

    def _deactivate_branches(self, output_names: list[str]) -> None:
        """Deactivate the given output branches so their downstream nodes do not execute.

        Mirrors SmartRouterComponent: `stop()` marks the branch INACTIVE for the current
        scheduling pass, while `exclude_branches_conditionally()` records a persistent exclusion
        so a re-activated branch that reconverges on a shared downstream node stays excluded.
        """
        for name in output_names:
            self.stop(name)
        # The persistent exclusion needs a real vertex/graph. Skip it when the component is
        # exercised without one (e.g. direct unit tests that mock `stop`).
        if self._vertex is None:
            return
        self._excluded_outputs.update(output_names)
        self._vertex.graph.exclude_branches_conditionally(self._id, sorted(self._excluded_outputs))

    @staticmethod
    def _as_data_payload(output: Any) -> dict[str, Any]:
        """Shape the validated output as the JSON payload carried by the Valid output."""
        if isinstance(output, dict):
            return output
        if isinstance(output, list):
            if len(output) == 1 and isinstance(output[0], dict):
                return output[0]
            return {"results": output}
        return {"result": output}

    def build_valid_output(self) -> Data:
        """Emit the schema-conforming output, or deactivate this branch when validation failed."""
        payload, errors, attempts = self._extract_and_validate()

        if errors:
            self._deactivate_branches(["valid_output"])
            violations = "\n".join(errors)
            self.status = f"Output rejected after {attempts} attempt(s):\n{violations}"
            return Data(data={})

        self._deactivate_branches(["invalid_output"])
        result = Data(data=self._as_data_payload(payload))
        self.status = result
        return result

    def build_invalid_output(self) -> Data:
        """Emit the rejected output together with the validation errors, for downstream handling."""
        payload, errors, attempts = self._extract_and_validate()

        if not errors:
            self._deactivate_branches(["invalid_output"])
            return Data(data={})

        self._deactivate_branches(["valid_output"])
        result = Data(
            data={
                "errors": errors,
                "attempts": attempts,
                "output": payload,
            }
        )
        self.status = result
        return result
