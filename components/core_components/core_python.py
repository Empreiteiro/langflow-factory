import importlib
import json

from langchain_experimental.utilities import PythonREPL

from langflow.custom.custom_component.component import Component
from langflow.io import MessageInput, Output, StrInput
from langflow.schema.data import Data
from langflow.schema.message import Message


class PythonREPLComponent(Component):
    display_name = "Python REPL"
    description = (
        "A Python code executor that lets you run Python code with specific imported modules. "
        "Remember to always use print() to see your results. Example: print(df.head())"
    )
    icon = "Python"

    inputs = [
        StrInput(
            name="global_imports",
            display_name="Global Imports",
            info="A comma-separated list of modules to import globally, e.g. 'math,numpy,pandas'.",
            value="math,pandas",
            required=True,
        ),
        MessageInput(
            name="python_code",
            display_name="Python Code",
            info="The Python code to execute. Only modules specified in Global Imports can be used.",
            value="print('Hello, World!')",
            tool_mode=True,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Results",
            name="results",
            type_=Data,
            method="run_python_repl",
        ),
    ]

    def get_globals(self, global_imports: str | list[str]) -> dict:
        """Create a globals dictionary with only the specified allowed imports."""
        global_dict = {}

        try:
            if isinstance(global_imports, str):
                modules = [module.strip() for module in global_imports.split(",")]
            elif isinstance(global_imports, list):
                modules = global_imports
            else:
                msg = "global_imports must be either a string or a list"
                raise TypeError(msg)

            for module in modules:
                try:
                    imported_module = importlib.import_module(module)
                    global_dict[imported_module.__name__] = imported_module
                except ImportError as e:
                    msg = f"Could not import module {module}: {e!s}"
                    raise ImportError(msg) from e

        except Exception as e:
            self.log(f"Error in global imports: {e!s}")
            raise
        else:
            self.log(f"Successfully imported modules: {list(global_dict.keys())}")
            return global_dict

    def _extract_code(self, message_input) -> str:
        """Extract executable code from different MessageInput payload formats."""

        def _extract_from_json(value):
            if isinstance(value, dict):
                for key in ("text", "content", "message", "value", "body", "result"):
                    if key in value and value[key]:
                        extracted = _extract_from_json(value[key])
                        if extracted:
                            return extracted
                for item in value.values():
                    extracted = _extract_from_json(item)
                    if extracted:
                        return extracted
                return ""
            if isinstance(value, list):
                for item in value:
                    extracted = _extract_from_json(item)
                    if extracted:
                        return extracted
                return ""
            if value is None:
                return ""
            return str(value)

        if message_input is None:
            return ""

        if isinstance(message_input, Message):
            return message_input.text or message_input.content or ""

        for attr in ("text", "content", "message"):
            if hasattr(message_input, attr):
                value = getattr(message_input, attr)
                if value:
                    return self._extract_code(value)

        if isinstance(message_input, dict):
            return _extract_from_json(message_input)

        if isinstance(message_input, list):
            return _extract_from_json(message_input)

        if isinstance(message_input, str):
            try:
                parsed = json.loads(message_input)
            except (json.JSONDecodeError, TypeError):
                return message_input
            return _extract_from_json(parsed)

        return str(message_input)

    def run_python_repl(self) -> Data:
        try:
            code = self._extract_code(self.python_code)
            globals_ = self.get_globals(self.global_imports)
            python_repl = PythonREPL(_globals=globals_)
            result = python_repl.run(code)
            result = result.strip() if result else ""
    
            self.log("Code execution completed successfully")
            return Data(data={"result": result})
    
        except ImportError as e:
            error_message = f"Import Error: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})
    
        except SyntaxError as e:
            error_message = f"Syntax Error: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})
    
        except (NameError, TypeError, ValueError) as e:
            error_message = f"Error during execution: {e!s}"
            self.log(error_message)
            return Data(data={"error": error_message})

    def build(self):
        return self.run_python_repl
