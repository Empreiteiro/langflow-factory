from lfx.custom import Component
from lfx.io import StrInput, MessageInput, Output
from lfx.schema import Data


class GetVarComponent(Component):
    display_name = "Get Var"
    description = "Retrieves a variable from the flow context."
    icon = "mdi-database-search"
    name = "GetVarComponent"

    inputs = [
        MessageInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger input to activate this component. Content is ignored.",
        ),
        StrInput(
            name="var_name",
            display_name="Variable Name",
            info="The name of the variable to retrieve.",
            required=True
        ),
    ]

    outputs = [
        Output(name="output", display_name="Variable Value", method="get_variable"),
    ]

    def get_variable(self) -> Data:
        try:
            value = self.ctx.get(self.var_name)
            if value is None:
                raise KeyError(f"Variable '{self.var_name}' not found.")
            return Data(data={"value": value})
        except Exception as e:
            self.status = f"Failed to retrieve variable: {e}"
            return Data(data={"error": self.status})
