from typing import Any

from langflow.custom import Component
from langflow.io import HandleInput, Output, TabInput
from langflow.schema import Data, DataFrame, Message


def convert_to_message(v) -> Message:
    """Convert input to Message type.

    Args:
        v: Input to convert (Message, Data, DataFrame, or dict)

    Returns:
        Message: Converted Message object
    """
    return v if isinstance(v, Message) else v.to_message()


def convert_to_data(v: DataFrame | Data | Message | dict) -> Data:
    """Convert input to Data type.

    Args:
        v: Input to convert (Message, Data, DataFrame, or dict)

    Returns:
        Data: Converted Data object
    """
    if isinstance(v, dict):
        return Data(v)
    if isinstance(v, Message):
        return v.to_data()
    return v if isinstance(v, Data) else v.to_data()


def convert_to_dataframe(v: DataFrame | Data | Message | dict | list) -> DataFrame:
    """Convert input to DataFrame type.

    Args:
        v: Input to convert (Message, Data, DataFrame, dict, or list of dicts)

    Returns:
        DataFrame: Converted DataFrame object
    """
    # Handle list of dictionaries (data list) - convert each dict to Data first
    if isinstance(v, list):
        # Check if it's a list of dictionaries
        if v and isinstance(v[0], dict):
            # Convert each dictionary to a Data object, then create DataFrame (like input.py)
            data_list = [Data(data=item) for item in v]
            return DataFrame(data_list)
        # If it's a list of Data objects, use directly
        elif v and isinstance(v[0], Data):
            return DataFrame(v)
        # If it's a list with a single item, extract it
        elif len(v) == 1:
            return convert_to_dataframe(v[0])
    
    # Handle single dictionary - convert to Data first, then wrap in list
    if isinstance(v, dict):
        data_list = [Data(data=v)]
        return DataFrame(data_list)
    
    # Handle Data object - check if it contains a list of dicts
    if isinstance(v, Data):
        data_value = v.data if hasattr(v, 'data') else v.value if hasattr(v, 'value') else v
        # If Data contains a list of dicts, convert each to Data first
        if isinstance(data_value, list) and data_value and isinstance(data_value[0], dict):
            data_list = [Data(data=item) for item in data_value]
            return DataFrame(data_list)
        # If Data contains a single dict, wrap in list and convert to Data
        if isinstance(data_value, dict):
            data_list = [Data(data=data_value)]
            return DataFrame(data_list)
    
    # Handle DataFrame directly (Langflow DataFrame)
    if isinstance(v, DataFrame):
        return v
    
    # Handle pandas DataFrame - wrap in Langflow DataFrame
    if hasattr(v, 'to_dict') and hasattr(v, 'columns'):
        # This looks like a pandas DataFrame
        return DataFrame(v)
    
    # Try to convert using to_dataframe method
    return v.to_dataframe()


class TypeConverterComponent(Component):
    display_name = "Type Convert"
    description = "Convert between different types (Message, Data, DataFrame)"
    documentation: str = "https://docs.langflow.org/components-processing#type-convert"
    icon = "repeat"

    inputs = [
        HandleInput(
            name="input_data",
            display_name="Input",
            input_types=["Message", "Data", "DataFrame"],
            info="Accept Message, Data or DataFrame as input",
            required=True,
        ),
        TabInput(
            name="output_type",
            display_name="Output Type",
            options=["Message", "Data", "DataFrame"],
            info="Select the desired output data type",
            real_time_refresh=True,
            value="Message",
        ),
    ]

    outputs = [
        Output(
            display_name="Message Output",
            name="message_output",
            method="convert_to_message",
        )
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically show only the relevant output based on the selected output type."""
        if field_name == "output_type":
            # Start with empty outputs
            frontend_node["outputs"] = []

            # Add only the selected output type
            if field_value == "Message":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Message Output",
                        name="message_output",
                        method="convert_to_message",
                    ).to_dict()
                )
            elif field_value == "Data":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Data Output",
                        name="data_output",
                        method="convert_to_data",
                    ).to_dict()
                )
            elif field_value == "DataFrame":
                frontend_node["outputs"].append(
                    Output(
                        display_name="DataFrame Output",
                        name="dataframe_output",
                        method="convert_to_dataframe",
                    ).to_dict()
                )

        return frontend_node

    def convert_to_message(self) -> Message:
        """Convert input to Message type."""
        input_value = self.input_data[0] if isinstance(self.input_data, list) else self.input_data

        # Handle string input by converting to Message first
        if isinstance(input_value, str):
            input_value = Message(text=input_value)

        result = convert_to_message(input_value)
        self.status = result
        return result

    def convert_to_data(self) -> Data:
        """Convert input to Data type."""
        input_value = self.input_data[0] if isinstance(self.input_data, list) else self.input_data

        # Handle string input by converting to Message first
        if isinstance(input_value, str):
            input_value = Message(text=input_value)

        result = convert_to_data(input_value)
        self.status = result
        return result

    def convert_to_dataframe(self) -> DataFrame:
        """Convert input to DataFrame type."""
        input_value = self.input_data[0] if isinstance(self.input_data, list) else self.input_data

        # Handle string input by converting to Message first
        if isinstance(input_value, str):
            input_value = Message(text=input_value)
        
        # Handle Data object that might contain a list of dicts
        if isinstance(input_value, Data):
            # Try to extract the actual data from Data object
            data_content = None
            if hasattr(input_value, 'data'):
                data_content = input_value.data
            elif hasattr(input_value, 'value'):
                data_content = input_value.value
            else:
                # Try to access as dict
                try:
                    data_content = dict(input_value) if input_value else None
                except (TypeError, ValueError):
                    pass
            
            # If Data contains a list of dicts, convert each to Data first, then create DataFrame
            if isinstance(data_content, list) and data_content:
                # Check if it's a list of dicts
                if isinstance(data_content[0], dict):
                    # Convert each dictionary to a Data object, then create DataFrame
                    data_list = [Data(data=item) for item in data_content]
                    result = DataFrame(data_list)
                    return result
                # If it's a list of Data objects, use directly
                elif isinstance(data_content[0], Data):
                    result = DataFrame(data_content)
                    return result
            
            # If Data contains a single dict, wrap in list and convert
            if isinstance(data_content, dict):
                data_list = [Data(data=data_content)]
                result = DataFrame(data_list)
                return result

        result = convert_to_dataframe(input_value)
        return result
