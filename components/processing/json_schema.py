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
    BoolInput,
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

DEFAULT_SYSTEM_PROMPT = (
    "You extract data from the input text into the given JSON Schema. "
    "Only use values that are stated in the input text or directly inferable from it. "
    "Never invent, guess or default a value to satisfy the schema: no placeholder names "
    "('Unknown', 'N/A', 'John Doe'), no made-up numbers or dates, no enum value picked at random. "
    "Leave an optional field out when the input does not support it. "
    "Never add keys that are not in the schema. "
    "If the input text does not contain the data the schema asks for, set extraction_succeeded to false "
    "and explain what is missing in reason, instead of filling the fields with invented values."
)

GROUNDING_SYSTEM_PROMPT = (
    "You are a strict auditor. You are given an input text and data that was extracted from it. "
    "For every value in the extracted data, decide whether it is explicitly stated in the input text "
    "or directly inferable from it. "
    "Placeholders ('Unknown', 'N/A', 'Desconhecido'), guessed numbers or dates, and values chosen only to "
    "satisfy a schema are NOT supported. "
    "List every unsupported value. If every value is supported by the input text, return an empty list."
)

GROUNDING_TOOL: dict[str, Any] = {
    "name": "GroundingReport",
    "description": "Report which values of the extracted data are not supported by the input text.",
    "parameters": {
        "type": "object",
        "properties": {
            "unsupported": {
                "type": "array",
                "description": (
                    "One entry per value that is not stated in, nor directly inferable from, the input text. "
                    "Empty when every value is supported."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": "Path of the offending field, e.g. 'name' or '0/age'.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why the value is not supported by the input text.",
                        },
                    },
                    "required": ["field", "reason"],
                },
            }
        },
        "required": ["unsupported"],
    },
}

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
            value=DEFAULT_SYSTEM_PROMPT,
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
        BoolInput(
            name="reject_extra_fields",
            display_name="Reject Extra Fields",
            info=(
                "Reject output that contains keys the schema does not declare. "
                "JSON Schema allows extra keys by default; this enforces the schema as a closed contract."
            ),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="verify_against_input",
            display_name="Verify Against Input",
            info=(
                "Run a second pass asking the model whether every extracted value is actually supported by "
                "the input text. Catches values that satisfy the schema but were invented (placeholder names, "
                "guessed numbers, an enum picked at random). Costs one extra model call."
            ),
            value=True,
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
    # Where a nested schema can hide, for the strict-mode rewrite.
    _SUBSCHEMA_KEYS = ("items", "additionalItems", "contains", "not", "if", "then", "else")
    _SUBSCHEMA_MAP_KEYS = ("properties", "$defs", "definitions", "patternProperties")
    _SUBSCHEMA_LIST_KEYS = ("anyOf", "allOf", "oneOf", "prefixItems")

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

    def _close_schema(self, schema: Any) -> Any:
        """Return a copy of the schema where every declared object rejects undeclared keys.

        JSON Schema allows extra keys unless the author says otherwise, so a model can pad the
        output with keys nobody asked for and still validate. This closes that gap for validation.
        """
        if isinstance(schema, list):
            return [self._close_schema(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        closed = dict(schema)
        for key in self._SUBSCHEMA_KEYS:
            if key in closed:
                closed[key] = self._close_schema(closed[key])
        for key in self._SUBSCHEMA_MAP_KEYS:
            if isinstance(closed.get(key), dict):
                closed[key] = {name: self._close_schema(sub) for name, sub in closed[key].items()}
        for key in self._SUBSCHEMA_LIST_KEYS:
            if isinstance(closed.get(key), list):
                closed[key] = [self._close_schema(sub) for sub in closed[key]]

        declares_object = "properties" in closed or closed.get("type") == "object"
        already_constrained = any(
            key in closed for key in ("additionalProperties", "unevaluatedProperties", "patternProperties")
        )
        # $ref/composition keywords bring in properties this copy cannot see, so leave those open.
        composes = any(key in closed for key in ("$ref", "anyOf", "allOf", "oneOf"))
        if declares_object and not already_constrained and not composes:
            closed["additionalProperties"] = False
        return closed

    def _build_tool(self, schema: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Wrap the user schema in an envelope the model can also use to report failure.

        `tool_choice` forces the model to call the tool, so without `extraction_succeeded` the model
        has no way to say "the input does not contain this data" and is pushed into inventing values.
        The payload itself stays under "data", untouched, so any top-level type works.
        """
        schema_name = (self.schema_name or schema.get("title") or "OutputModel").strip() or "OutputModel"
        description = schema.get("description", f"Output conforming to {schema_name}.")

        parameters = {
            "type": "object",
            "description": description,
            "properties": {
                "extraction_succeeded": {
                    "type": "boolean",
                    "description": (
                        "True only when the input text actually contains the data the schema asks for. "
                        "False when the data is absent and would have to be invented."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "When extraction_succeeded is false, what is missing from the input text.",
                },
                "data": schema,
            },
            "required": ["extraction_succeeded"],
        }
        tool = {"name": schema_name, "description": description, "parameters": parameters}
        return tool, schema_name

    def _call_extractor(self, llm, tool: dict[str, Any], tool_name: str, system_message: str, input_value: str) -> Any:
        """Run one structured-output call through trustcall."""
        try:
            extractor = create_extractor(llm, tools=[tool], tool_choice=tool_name)
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
            system_message=system_message,
            input_value=input_value,
            config=config_dict,
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response from the model: {type(result).__name__}."
            raise ValueError(msg)

        responses = result.get("responses", [])
        if not responses:
            msg = "The model returned no output for the provided schema."
            raise ValueError(msg)

        first_response = responses[0]
        return first_response.model_dump() if isinstance(first_response, BaseModel) else first_response

    def _run_extraction(self, llm, tool: dict[str, Any], tool_name: str, prompt: str) -> tuple[Any, bool, str]:
        """Return (payload, succeeded, reason) from one extraction attempt."""
        envelope = self._call_extractor(llm, tool, tool_name, prompt, self.input_value)
        if not isinstance(envelope, dict):
            msg = f"Unexpected response from the model: {type(envelope).__name__}."
            raise ValueError(msg)

        succeeded = bool(envelope.get("extraction_succeeded", True))
        reason = str(envelope.get("reason") or "")
        payload = envelope.get("data")
        return payload, succeeded, reason

    def _validate_payload(self, payload: Any, schema: dict[str, Any]) -> list[str]:
        """Return a list of human-readable schema violations. An empty list means the payload is valid."""
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            return self._validate_with_pydantic(payload, schema)

        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(payload))
        except Exception as exc:  # noqa: BLE001
            msg = f"The provided JSON Schema is not a valid schema: {exc}"
            raise ValueError(msg) from exc

        messages = [f"{self._error_path(error.absolute_path)}: {error.message}" for error in errors]
        return self._truncate_errors(messages)

    def _validate_with_pydantic(self, payload: Any, schema: dict[str, Any]) -> list[str]:
        """Fallback validation via dydantic, the schema-to-pydantic library trustcall already depends on.

        Used only when `jsonschema` is not installed. It is best-effort: pydantic coerces some
        scalars and dydantic does not enforce every JSON Schema keyword, so it catches missing
        required fields and wrong types but can let subtler constraints through.
        """
        from dydantic import create_model_from_schema
        from pydantic import ValidationError

        # dydantic needs an object at the root, so a top-level array is validated through a wrapper.
        wrapped = schema.get("type") == "array"
        if wrapped:
            schema = {"type": "object", "properties": {"items": schema}, "required": ["items"]}
            payload = {"items": payload}

        try:
            model = create_model_from_schema(schema)
        except Exception as exc:  # noqa: BLE001
            msg = f"The provided JSON Schema is not a valid schema: {exc}"
            raise ValueError(msg) from exc

        try:
            model.model_validate(payload)
        except ValidationError as exc:
            messages = [
                f"{self._error_path(error['loc'], strip_first='items' if wrapped else None)}: {error['msg']}"
                for error in exc.errors()
            ]
            return self._truncate_errors(messages)
        return []

    @staticmethod
    def _error_path(path, strip_first: str | None = None) -> str:
        """Render the location of a violation as a path, e.g. `0/name`."""
        parts = [str(part) for part in path]
        if strip_first and parts and parts[0] == strip_first:
            parts = parts[1:]
        return "/".join(parts) or "<root>"

    @staticmethod
    def _truncate_errors(messages: list[str]) -> list[str]:
        if len(messages) <= MAX_REPORTED_ERRORS:
            return messages
        hidden = len(messages) - MAX_REPORTED_ERRORS
        return [*messages[:MAX_REPORTED_ERRORS], f"... and {hidden} more validation error(s)."]

    def _check_grounding(self, llm, payload: Any) -> list[str]:
        """Ask the model which extracted values are not supported by the input text.

        Schema validation only checks shape: an invented name of the right type passes every
        constraint. This is what catches it. Errors from the audit call itself are logged and
        ignored, so a transient failure of the auditor does not fail an otherwise valid output.
        """
        extracted = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
        audit_input = f"INPUT TEXT:\n{self.input_value}\n\nEXTRACTED DATA:\n{extracted}"
        try:
            report = self._call_extractor(
                llm, GROUNDING_TOOL, GROUNDING_TOOL["name"], GROUNDING_SYSTEM_PROMPT, audit_input
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"Could not verify the output against the input, skipping that check: {exc}")
            return []

        if not isinstance(report, dict):
            return []
        unsupported = report.get("unsupported") or []
        messages = [
            f"{item.get('field') or '<root>'}: not supported by the input text - {item.get('reason', '')}".strip()
            for item in unsupported
            if isinstance(item, dict)
        ]
        return self._truncate_errors(messages)

    def _extract_and_validate(self) -> tuple[Any, list[str], int]:
        """Extract, validate and retry with the validation errors fed back into the prompt.

        Returns (payload, errors, attempts). The LLM is only called once per component run, no
        matter how many outputs are connected, because the result is cached.

        Schema violations are retried; a model that reports it could not extract the data, and
        values that are not supported by the input, are not - retrying only invites another
        invented answer.
        """
        if self._extraction_result is not None:
            return self._extraction_result

        llm = get_llm(model=self.model, user_id=self.user_id, api_key=self.api_key)
        if not hasattr(llm, "with_structured_output"):
            msg = "Language model does not support structured output."
            raise TypeError(msg)

        schema = self._parse_json_schema()
        tool, tool_name = self._build_tool(schema)
        validation_schema = self._close_schema(schema) if getattr(self, "reject_extra_fields", True) else schema

        attempts = max(int(getattr(self, "max_retries", 1) or 0), 0) + 1
        base_prompt = self.system_prompt
        prompt = base_prompt
        payload: Any = None
        errors: list[str] = []
        extraction_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                payload, succeeded, reason = self._run_extraction(llm, tool, tool_name, prompt)
            except TypeError:
                raise
            except Exception as exc:  # noqa: BLE001
                # Keep trying: a transient failure may still succeed on the next attempt.
                extraction_error = exc
                self.log(f"Attempt {attempt}/{attempts} failed to produce output: {exc}")
                continue

            extraction_error = None

            if not succeeded:
                detail = reason or "the input text does not contain the data the schema asks for"
                failure = f"<root>: the model could not extract the data - {detail}"
                self._extraction_result = (payload, [failure], attempt)
                return self._extraction_result

            if payload is None:
                errors = ["<root>: the model reported success but returned no data."]
            else:
                errors = self._validate_payload(payload, validation_schema)

            if not errors:
                if getattr(self, "verify_against_input", True):
                    errors = self._check_grounding(llm, payload)
                    if errors:
                        self.log(f"Attempt {attempt}/{attempts} produced values not supported by the input: {errors}")
                        self._extraction_result = (payload, errors, attempt)
                        return self._extraction_result
                self._extraction_result = (payload, [], attempt)
                return self._extraction_result

            self.log(f"Attempt {attempt}/{attempts} produced output that violates the schema: {errors}")
            violations = "\n".join(f"- {error}" for error in errors)
            prompt = (
                f"{base_prompt}\n\n"
                f"A previous attempt returned this output:\n{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
                f"It was rejected because it violates the schema:\n{violations}\n\n"
                f"Return a corrected output that fixes every violation above. "
                f"Do not invent values to satisfy the schema: if the input text does not contain the data, "
                f"set extraction_succeeded to false instead."
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
