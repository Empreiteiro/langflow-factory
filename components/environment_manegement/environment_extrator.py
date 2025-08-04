from langflow.custom import Component
from langflow.io import StrInput, Output
from langflow.schema import Data

class ApiKeyPrinter(Component):
    display_name = "Environment Variable Printer"
    description = "⚠️ Prints the selected environment variable." 
    icon = "mdi-key-variant"
    name = "ApiKeyPrinter"

    inputs = [
        StrInput(
            name="environment_variable",
            display_name="Environment Variable",
            info="Selecte the environment variable to print.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="variable", display_name="Variable", method="print_environment"),
    ]

    def print_environment(self) -> Data:
        try:
            self.log(f"Environment Variable: {self.environment_variable}")
            return Data(data={"value": self.environment_variable})
        except Exception as e:
            self.status = f"Error: {str(e)}"
            return Data(data={"error": str(e)})
