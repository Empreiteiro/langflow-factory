import json
from typing import Any, List, Literal, Optional, Type

from pydantic import BaseModel, Field, ValidationError, create_model

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    MultilineInput,
    Output,
    TableInput,
)
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.table import EditMode


_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
}


class EnhancedStructuredOutputComponent(Component):
    display_name = "Structured Output (with Choices)"
    description = (
        "Uses an LLM to produce structured data validated against a Pydantic / JSON Schema. "
        "Each field can declare a list of allowed values, forcing the LLM to pick from a closed set."
    )
    icon = "braces"
    name = "EnhancedStructuredOutput"

    inputs = [
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="The language model used to generate the structured output.",
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="input_value",
            display_name="Input Message",
            info="Unstructured text the LLM should extract values from.",
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="Format Instructions",
            info="System prompt describing the extraction task.",
            value=(
                "You extract structured data from unstructured text. Return ONLY JSON that "
                "conforms to the provided schema. When a field has an explicit list of allowed "
                "values, you MUST pick one of them verbatim. If a value cannot be determined, "
                "return null for that field."
            ),
            advanced=True,
        ),
        MessageTextInput(
            name="schema_name",
            display_name="Schema Name",
            info="Name of the generated Pydantic model.",
            value="OutputModel",
            advanced=True,
        ),
        TableInput(
            name="output_schema",
            display_name="Output Schema",
            info=(
                "Define the output fields. 'Allowed Values' accepts a comma-separated list "
                "(e.g. 'low, medium, high') or a JSON array."
            ),
            required=True,
            table_schema=[
                {
                    "name": "name",
                    "display_name": "Name",
                    "type": "str",
                    "description": "Field name.",
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": "Description",
                    "type": "str",
                    "description": "What the field represents (passed to the LLM).",
                    "default": "",
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "type",
                    "display_name": "Type",
                    "type": "str",
                    "description": "Data type (str, int, float, bool, dict).",
                    "options": ["str", "int", "float", "bool", "dict"],
                    "default": "str",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "multiple",
                    "display_name": "As List",
                    "type": "boolean",
                    "description": "Emit a list of the specified type.",
                    "default": "False",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "required",
                    "display_name": "Required",
                    "type": "boolean",
                    "description": "Whether the field must be present.",
                    "default": "True",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "allowed_values",
                    "display_name": "Allowed Values",
                    "type": "str",
                    "description": (
                        "Closed set of accepted values. Comma-separated or JSON array. "
                        "Empty = no constraint."
                    ),
                    "default": "",
                    "edit_mode": EditMode.POPOVER,
                },
            ],
            value=[
                {
                    "name": "category",
                    "description": "Category of the input.",
                    "type": "str",
                    "multiple": "False",
                    "required": "True",
                    "allowed_values": "positive, negative, neutral",
                }
            ],
        ),
        DropdownInput(
            name="validation_mode",
            display_name="Validation Mode",
            info=(
                "'pydantic' relies on the model's built-in structured-output support; "
                "'json_schema' asks for JSON text and validates it locally against the schema."
            ),
            options=["pydantic", "json_schema"],
            value="pydantic",
        ),
        BoolInput(
            name="output_as_list",
            display_name="Extract Multiple",
            info="Wrap the schema in a list so the LLM can return several matching objects.",
            value=False,
        ),
        BoolInput(
            name="strict_mode",
            display_name="Strict",
            info="Raise on validation errors. When off, invalid fields fall back to null.",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="data", display_name="Structured Output", method="build_data"),
        Output(name="dataframe", display_name="DataFrame", method="build_dataframe"),
        Output(name="schema", display_name="JSON Schema", method="build_schema"),
    ]

    # -------- schema construction --------

    @staticmethod
    def _parse_allowed(raw: Any) -> List[Any]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [v for v in raw if v not in (None, "")]
        if not isinstance(raw, str):
            return [raw]
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return [p.strip() for p in text.split(",") if p.strip()]

    @staticmethod
    def _coerce_value(value: Any, target_type: str) -> Any:
        caster = _TYPE_MAP.get(target_type, str)
        try:
            if caster is bool and isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes"}
            return caster(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return bool(value)

    def _build_field(self, row: dict) -> tuple[type, Any]:
        base_type_name = (row.get("type") or "str").strip().lower()
        base_type = _TYPE_MAP.get(base_type_name, str)

        allowed_raw = self._parse_allowed(row.get("allowed_values"))
        allowed = [self._coerce_value(v, base_type_name) for v in allowed_raw]

        if allowed:
            field_type: Any = Literal[tuple(allowed)]  # type: ignore[valid-type]
        else:
            field_type = base_type

        if self._is_truthy(row.get("multiple")):
            field_type = list[field_type]  # type: ignore[valid-type]

        required = self._is_truthy(row.get("required", True))
        description = row.get("description") or ""

        if allowed:
            description = (
                f"{description}\nAllowed values: {allowed}. Return exactly one of them."
                if description
                else f"Allowed values: {allowed}. Return exactly one of them."
            )

        if required:
            return field_type, Field(..., description=description)
        field_type = Optional[field_type]  # type: ignore[assignment]
        return field_type, Field(default=None, description=description)

    def _build_model(self) -> tuple[Type[BaseModel], list[dict]]:
        if not self.output_schema:
            raise ValueError("Output schema cannot be empty.")
        rows = list(self.output_schema)
        fields: dict[str, tuple[Any, Any]] = {}
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError("Each schema row must have a non-empty 'name'.")
            fields[name] = self._build_field(row)

        model_name = (self.schema_name or "OutputModel").strip() or "OutputModel"
        model = create_model(model_name, **fields)  # type: ignore[call-overload]

        if self.output_as_list:
            list_model = create_model(
                f"{model_name}List",
                items=(list[model], Field(..., description=f"A list of {model_name}.")),
            )
            return list_model, rows
        return model, rows

    # -------- execution --------

    def _run_pydantic(self, model: Type[BaseModel]) -> BaseModel:
        if not hasattr(self.llm, "with_structured_output"):
            raise TypeError(
                "The provided language model does not implement with_structured_output(). "
                "Switch Validation Mode to 'json_schema' to fall back to text parsing."
            )
        runnable = self.llm.with_structured_output(model)
        prompt = self._compose_prompt()
        result = runnable.invoke(prompt)
        if isinstance(result, BaseModel):
            return result
        if isinstance(result, dict):
            return model.model_validate(result)
        raise TypeError(f"Unexpected structured-output response type: {type(result)}")

    def _run_json_schema(self, model: Type[BaseModel]) -> BaseModel:
        schema = model.model_json_schema()
        schema_text = json.dumps(schema, indent=2, ensure_ascii=False)
        instruction = (
            f"{self.system_prompt}\n\nRespond ONLY with JSON that conforms to this schema:\n"
            f"{schema_text}\n\nDo not wrap the JSON in markdown fences."
        )
        prompt = f"{instruction}\n\nInput:\n{self.input_value}"
        response = self.llm.invoke(prompt)
        text = getattr(response, "content", response)
        if isinstance(text, list):
            text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
        text = str(text).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON: {exc}\nResponse: {text}") from exc
        return model.model_validate(payload)

    def _compose_prompt(self) -> str:
        return f"{self.system_prompt}\n\nInput:\n{self.input_value}"

    def _run(self):
        model, _ = self._build_model()
        self._schema = model.model_json_schema()
        try:
            if self.validation_mode == "json_schema":
                instance = self._run_json_schema(model)
            else:
                instance = self._run_pydantic(model)
        except ValidationError as exc:
            if self.strict_mode:
                raise
            self.log(f"Validation errors ignored (strict_mode=False): {exc}")
            instance = model.model_construct()
        self._instance = instance
        self._output = instance.model_dump()
        self.log(f"EnhancedStructuredOutput produced {len(self._output)} top-level key(s)")

    # -------- outputs --------

    def build_data(self) -> Data:
        try:
            if not hasattr(self, "_output"):
                self._run()
            data = self._output
            if self.output_as_list and isinstance(data, dict) and "items" in data:
                items = data["items"]
                if len(items) == 1:
                    return Data(data=items[0])
                return Data(data={"results": items})
            return Data(data=data)
        except Exception as exc:
            self.log(f"EnhancedStructuredOutput failed: {exc}")
            return Data(data={"error": str(exc)})

    def build_dataframe(self) -> DataFrame:
        import pandas as pd
        try:
            if not hasattr(self, "_output"):
                self._run()
            data = self._output
            if self.output_as_list and isinstance(data, dict) and "items" in data:
                return DataFrame(pd.DataFrame(data["items"]))
            return DataFrame(pd.DataFrame([data]))
        except Exception as exc:
            self.log(f"EnhancedStructuredOutput DataFrame failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def build_schema(self) -> Data:
        try:
            if not hasattr(self, "_schema"):
                model, _ = self._build_model()
                self._schema = model.model_json_schema()
            return Data(data=self._schema)
        except Exception as exc:
            return Data(data={"error": str(exc)})
