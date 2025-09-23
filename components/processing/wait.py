from lfx.custom import Component
from lfx.io import IntInput, Output, MessageTextInput, DataInput, TabInput
from lfx.schema import Data
from lfx.schema.message import Message
import time
from typing import Any

class Wait(Component):
    display_name = "Wait"
    description = "Pauses execution for a specified number of seconds."
    icon = "Timer"
    name = "WaitComponent"

    inputs = [
        TabInput(
            name="output_type",
            display_name="Output Type",
            options=["Message", "Data"],
            info="Select the desired output data type. This will show the corresponding input field.",
            real_time_refresh=True,
            value="Message",
        ),
        IntInput(
            name="seconds",
            display_name="Wait Time (seconds)",
            info="Number of seconds to wait before continuing execution (1-3600).",
            required=True
        ),
        MessageTextInput(
            name="message_input",
            display_name="Message Input",
            info="Message input to pass through after waiting.",
            show=False
        ),
        DataInput(
            name="data_input",
            display_name="Data Input",
            info="Data input to pass through after waiting.",
            show=False
        )
    ]

    outputs = [
        Output(
            display_name="Message Output",
            name="message_output",
            method="wait_message_output",
        )
    ]

    def _wait_internal(self) -> dict:
        """Internal method to perform wait and return status."""
        try:
            # Get wait time
            wait_seconds = getattr(self, 'seconds', 1) or 1
            
            # Validate wait time
            if wait_seconds < 1:
                wait_seconds = 1
            elif wait_seconds > 3600:
                wait_seconds = 3600
            
            self.status = f"Waiting for {wait_seconds} seconds..."
            self.log(f"Starting wait for {wait_seconds} seconds")
            
            # Perform the wait
            time.sleep(wait_seconds)
            
            self.status = f"Wait completed! Waited for {wait_seconds} seconds."
            self.log(f"Wait completed successfully after {wait_seconds} seconds")
            
            return {
                "wait_time_seconds": wait_seconds,
                "status": "completed",
                "message": f"Successfully waited for {wait_seconds} seconds"
            }
            
        except Exception as e:
            error_msg = f"Error during wait: {str(e)}"
            self.status = f"Error: {error_msg}"
            self.log(error_msg)
            return {
                "error": error_msg,
                "status": "error"
            }



    def update_build_config(self, build_config, field_value, field_name=None):
        """Dynamically show only the relevant input based on the selected output type."""
        if field_name != "output_type":
            return build_config

        # Extract output type from the selected option
        output_type = field_value if isinstance(field_value, str) else "Message"

        # Hide all dynamic fields first
        for field_name in ["message_input", "data_input"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected output type
        if output_type == "Message":
            if "message_input" in build_config:
                build_config["message_input"]["show"] = True
        elif output_type == "Data":
            if "data_input" in build_config:
                build_config["data_input"]["show"] = True

        return build_config

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
                        method="wait_message_output",
                    ).to_dict()
                )
            elif field_value == "Data":
                frontend_node["outputs"].append(
                    Output(
                        display_name="Data Output",
                        name="data_output",
                        method="wait_data_output",
                    ).to_dict()
                )

        return frontend_node

    def wait_message_output(self) -> Message:
        """Wait and return input as Message."""
        result = self._wait_internal()
        
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        
        # Get message input
        if hasattr(self.message_input, 'text'):
            text_content = self.message_input.text
        else:
            text_content = str(self.message_input) if self.message_input else ""
        
        if text_content:
            return Message(text=text_content)
        else:
            return Message(text=f"Wait completed. No message input provided.")

    def wait_data_output(self) -> Data:
        """Wait and return input as Data."""
        result = self._wait_internal()
        
        if "error" in result:
            return Data(data={"error": result["error"]})
        
        # Get data input
        if hasattr(self.data_input, 'data'):
            data_content = self.data_input.data
        else:
            data_content = self.data_input if self.data_input else {}
        
        if data_content:
            return Data(data=data_content)
        else:
            return Data(data={
                **result,
                "note": "No data input provided"
            }) 
