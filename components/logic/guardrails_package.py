from langflow.custom import Component
from langflow.io import StrInput, MultilineInput, Output
from langflow.schema import Data
from guardrails import Guard
from guardrails.hub import register_validator

class GuardrailsValidator(Component):
    display_name = "Guardrails Validator"
    description = "Validates and corrects model outputs using Guardrails AI schemas and validators."
    icon = "shield-check"
    name = "GuardrailsValidator"

    inputs = [
        StrInput(
            name="schema_path",
            display_name="RAIL Schema Path",
            info="Path or URL to a .rail schema file defining the validation rules.",
            required=True,
        ),
        MultilineInput(
            name="input_text",
            display_name="Input Text",
            info="The text or JSON output to validate and correct using Guardrails.",
            required=True,
        ),
        StrInput(
            name="llm_model",
            display_name="LLM Model (Optional)",
            info="Optional model name used for correction (e.g., 'gpt-4'). Leave blank to skip correction.",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Validated Output", name="validated_output", method="validate_output"),
        Output(display_name="Validation Report", name="validation_report", method="validation_report")
    ]

    field_order = ["schema_path", "input_text", "llm_model"]

    def build(self):
        """Optional pre-validation setup."""
        self.log("Guardrails Validator initialized.")

    def _run_guardrails(self):
        """Run Guardrails validation."""
        try:
            self.log(f"Loading Guard schema from: {self.schema_path}")
            guard = Guard.from_rail(self.schema_path)

            self.log("Executing Guard validation...")
            result = guard(
                self.input_text,
                llm_api=self.llm_model if self.llm_model else None
            )

            self.log("Validation complete.")
            return result
        except Exception as e:
            error_message = f"Guardrails validation failed: {str(e)}"
            self.status = error_message
            self.log(error_message)
            return {"error": error_message}

    def validate_output(self) -> Data:
        """Return the validated and corrected output."""
        result = self._run_guardrails()
        if isinstance(result, dict) and "error" in result:
            return Data(data=result)
        try:
            return Data(data=result.validated_output)
        except Exception:
            return Data(data={"validated_output": str(result)})

    def validation_report(self) -> Data:
        """Return a detailed validation report including any corrections or errors."""
        result = self._run_guardrails()
        if isinstance(result, dict) and "error" in result:
            return Data(data=result)
        try:
            report = {
                "raw_output": result.raw_output,
                "validated_output": result.validated_output,
                "validation_passed": result.validation_passed,
                "error_messages": result.error_messages
            }
            return Data(data=report)
        except Exception as e:
            error_report = {"error": f"Failed to build report: {str(e)}"}
            self.status = error_report["error"]
            return Data(data=error_report)
