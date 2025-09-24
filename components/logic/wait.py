import time
from typing import Any

from langflow.custom import Component
from langflow.io import FloatInput, HandleInput, Output
from langflow.schema.data import Data
from langflow.schema.dataframe import DataFrame
from langflow.field_typing.range_spec import RangeSpec
from langflow.schema.message import Message


class WaitComponent(Component):
    display_name = "Wait"
    description = "Adds a configurable delay to workflow execution. Returns input data unchanged after specified time."
    icon = "clock"
    name = "WaitComponent"

    inputs = [
        HandleInput(
            name="input_data",
            display_name="Input",
            info="Any type of input that will be returned after the delay period.",
            input_types=["Text", "Data", "DataFrame", "Message"],
            required=True,
        ),
        FloatInput(
            name="delay_seconds",
            display_name="Delay (seconds)",
            info="Number of seconds to wait before returning the input data.",
            value=1.0,
            range_spec=RangeSpec(min=0, max=3600, step=1),
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Text Output", name="text_output", method="get_text_output"),
        Output(display_name="Data Output", name="data_output", method="get_data_output"),
        Output(display_name="DataFrame Output", name="dataframe_output", method="get_dataframe_output"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate_inputs(self) -> None:
        """Validate all component inputs before processing."""
        delay = getattr(self, "delay_seconds", 0.0)
        if delay < 0:
            raise ValueError("Delay must be non-negative")
        if delay > 3600:
            raise ValueError("Delay cannot exceed 3600 seconds (1 hour)")

    def _perform_wait(self) -> Any:
        """Internal method to perform the wait and return input data."""
        try:
            # Validate inputs first
            self.validate_inputs()
            
            # Get input data and delay
            input_data = getattr(self, "input_data", None)
            delay_seconds = getattr(self, "delay_seconds", 1.0)
            
            if input_data is None:
                self.log("No input data provided")
                return None
            
            # Log the wait operation
            self.log(f"Waiting for {delay_seconds} seconds...")
            
            # Perform the wait
            time.sleep(delay_seconds)
            
            # Log completion
            self.log(f"Wait completed. Returning input data.")
            
            # Return the original input data unchanged
            return input_data
            
        except Exception as e:
            self.log(f"Wait component failed: {str(e)}")
            return None

    def get_text_output(self) -> str:
        """Wait and return input data as text - no conversion."""
        input_data = self._perform_wait()
        if input_data is None:
            return "No input data provided"
        
        # Return original data without any conversion
        self.log("Returning original text data without conversion")
        return input_data

    def get_data_output(self) -> Data:
        """Wait and return input data as Data object - no conversion."""
        input_data = self._perform_wait()
        if input_data is None:
            return Data(data={"error": "No input data provided"})
        
        # Return original data without any conversion
        self.log("Returning original data without conversion")
        return input_data

    def get_dataframe_output(self) -> DataFrame:
        """Wait and return input data as DataFrame - no conversion."""
        input_data = self._perform_wait()
        if input_data is None:
            import pandas as pd
            return DataFrame(pd.DataFrame({"error": ["No input data provided"]}))
        
        # Return original data without any conversion
        self.log("Returning original DataFrame without conversion")
        return input_data
