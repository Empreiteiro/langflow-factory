from langflow.custom import Component
from langflow.io import StrInput, Output
from langflow.schema import Data


class SetVarComponent(Component):
    display_name = "Set Var"
    description = "Stores a variable in the flow context."
    icon = "mdi-database-plus"
    name = "SetVarComponent"

    inputs = [
        StrInput(
            name="var_name",
            display_name="Variable Name",
            info="The name of the variable to store.",
            required=True
        ),
        StrInput(
            name="var_value",
            display_name="Variable Value",
            info="The value of the variable to store.",
            required=True
        ),
    ]

    outputs = [
        Output(name="output", display_name="Status", method="store_variable"),
    ]

    def store_variable(self) -> Data:
        try:
            self.update_ctx({self.var_name: self.var_value})
            return Data(data={"status": f"Variable '{self.var_name}' set successfully."})
        except Exception as e:
            self.status = f"Failed to set variable: {e}"
            return Data(data={"error": self.status})
