from langflow.custom import Component
from langflow.io import StrInput, DropdownInput, Output
import os

class SQLiteConnectionString(Component):
    display_name = "SQLite String"
    description = "Creates a SQLite connection string from a file path and operating system."
    icon = "database"
    name = "SQLiteConnectionString"

    inputs = [
        StrInput(
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
        Output(name="text", display_name="Connection String", method="get_text"),
    ]

    def build(self):
        """Process the inputs and build the connection string."""
        try:
            if not self.path:
                raise ValueError("The file path is required.")

            # Extract text if it's a Message object
            if hasattr(self.path, 'text'):
                path = self.path.text
            elif hasattr(self.path, 'content'):
                path = self.path.content
            else:
                path = str(self.path)

            if self.os.lower() == "windows":
                path = path.replace("\\", "/")
                if not path.startswith("/"):
                    path = f"/{path}"
                conn_str = f"sqlite:///{path}"
            else:
                if not path.startswith("/"):
                    path = f"/{path}"
                conn_str = f"sqlite:////{path.lstrip('/')}"

            self.connection_string = conn_str
            self.status = f"Successfully created connection string: {conn_str}"
            self.log(self.status)

        except Exception as e:
            error_message = f"Error building connection string: {str(e)}"
            self.status = error_message
            self.log(error_message)
            self.connection_string = None

    def get_text(self) -> str:
        """Return the connection string as text."""
        if hasattr(self, 'connection_string') and self.connection_string:
            return self.connection_string
        return getattr(self, 'status', 'Unknown error')
