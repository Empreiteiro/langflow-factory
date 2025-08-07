from langflow.custom import Component
from langflow.io import StrInput, DropdownInput, Output
from langflow.schema.message import Message
import os

class SQLiteConnectionString(Component):
    display_name = "SQLite String"
    description = "Creates a SQLite connection string from a file path and operating system."
    icon = "database"
    name = "SQLiteConnectionString"

    inputs = [
        MessageInput(
            name="path",
            display_name="File Path",
            info="Absolute path to the .sqlite file",
            required=True,
        ),
        DropdownInput(
            name="os",
            display_name="Operating System",
            info="Operating system where the file is located",
            options=["Linux", "Windows", "macOS"],
            required=True,
        ),
    ]

    outputs = [
        Output(name="connection_string", display_name="Connection String", method="build"),
    ]

    def build(self) -> Message:
        try:
            if not self.path:
                raise ValueError("The file path is required.")

            path = self.path

            if self.os.lower() == "windows":
                path = path.replace("\\", "/")
                if not path.startswith("/"):
                    path = f"/{path}"
                conn_str = f"sqlite:///{path}"
            else:
                if not path.startswith("/"):
                    path = f"/{path}"
                conn_str = f"sqlite:////{path.lstrip('/')}"

            return Message(text=conn_str)
        except Exception as e:
            error_message = f"Error building connection string: {str(e)}"
            self.status = error_message
            return Message(text=error_message)
