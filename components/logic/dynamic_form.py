from langflow.custom import Component
from langflow.io import StrInput, IntInput, BoolInput, MultilineInput, TableInput, Output, SecretStrInput, FloatInput, HandleInput
from langflow.schema.message import Message
from langflow.schema.data import Data

from typing import Any, Dict, List
import json


class AdvancedDynamicFormBuilderComponent(Component):
    """
    Dynamic Form Component
    
    This component creates dynamic inputs that can receive data from other components
    or be filled manually. It demonstrates advanced dynamic input functionality with
    component connectivity.
    
    ## Features
    - **Dynamic Input Generation**: Create inputs based on table configuration
    - **Component Connectivity**: Inputs can receive data from other components
    - **Multiple Input Types**: Support for text, number, boolean, and handle inputs
    - **Flexible Data Sources**: Manual input OR component connections
    - **Real-time Updates**: Form fields update immediately when table changes
         - **Multiple Output Formats**: Data and formatted Message outputs
    - **JSON Output**: Collects all dynamic inputs into a structured JSON response
    
    ## Use Cases
    - Dynamic API parameter collection from multiple sources
    - Variable data aggregation from different components
    - Flexible pipeline configuration
    - Multi-source data processing
    
    ## Field Types Available
    - **text**: Single-line text input (can connect to Text/String outputs)
    - **multiline**: Multi-line text input (can connect to Text outputs)
    - **number**: Integer input (can connect to Number outputs)
    - **float**: Decimal number input (can connect to Number outputs)
    - **boolean**: True/false checkbox (can connect to Boolean outputs)
    - **handle**: Generic data input (can connect to any component output)
    - **data**: Structured data input (can connect to Data outputs)
    
    ## Input Types for Connections
    - **Text**: Text/String data from components
    - **Data**: Structured data objects
    - **Message**: Message objects with text content
    - **Number**: Numeric values
    - **Boolean**: True/false values
    - **Any**: Accepts any type of connection
    - **Combinations**: Text,Message | Data,Text | Text,Data,Message | etc.
    """
    
    display_name = "Dynamic Form"
    description = "Creates dynamic input fields that can receive data from other components or manual input."
    icon = "network"
    name = "AdvancedDynamicFormBuilder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dynamic_inputs = {}

    inputs = [
        TableInput(
            name="form_fields",
            display_name="Input Configuration",
            info="Define the dynamic form fields. Each row creates a new input field that can connect to other components.",
            table_schema=[
                {
                    "name": "field_name", 
                    "display_name": "Field Name", 
                    "type": "str", 
                    "description": "Internal name for the field (no spaces, use underscore)"
                },
                {
                    "name": "display_name", 
                    "display_name": "Display Name", 
                    "type": "str", 
                    "description": "User-friendly label for the field"
                },
                {
                    "name": "field_type", 
                    "display_name": "Field Type", 
                    "type": "str", 
                    "description": "Type of input field to create",
                    "options": ["text", "multiline", "number", "float", "boolean", "handle", "data"],
                    "value": "text"
                },
                {
                    "name": "default_value", 
                    "display_name": "Default Value", 
                    "type": "str", 
                    "description": "Default value for the field (used when no component connected)"
                },
                {
                    "name": "required", 
                    "display_name": "Required", 
                    "type": "str", 
                    "description": "Is this field required?",
                    "options": ["false", "true"],
                    "value": "false"
                },
                {
                    "name": "input_types", 
                    "display_name": "Input Types", 
                    "type": "str", 
                    "description": "Accepted input types for connections (only for handle/data fields)",
                    "options": [
                        "",
                        "Text",
                        "Data", 
                        "Message",
                        "Text,Message",
                        "Data,Text",
                        "Data,Message",
                        "Text,Data,Message",
                        "Number",
                        "Boolean",
                        "Any"
                    ],
                    "value": ""
                },
                {
                    "name": "help_text", 
                    "display_name": "Help Text", 
                    "type": "str", 
                    "description": "Help text for the field"
                }
            ],
            value=[
                {
                    "field_name": "person_name",
                    "display_name": "person_name", 
                    "field_type": "text",
                    "default_value": "",
                    "required": "false",
                    "input_types": "Text,Message",
                    "help_text": ""
                },
                {
                    "field_name": "person_age",
                    "display_name": "person_age", 
                    "field_type": "number",
                    "default_value": "",
                    "required": "false",
                    "input_types": "Text,Message",
                    "help_text": ""
                }
            ],
            real_time_refresh=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name="Include Metadata",
            info="Include form configuration metadata in the output.",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Data", 
            name="form_data", 
            method="process_form"
        ),
        Output(
            display_name="Message", 
            name="message", 
            method="get_message"
        ),
    ]

    def update_build_config(self, build_config: Dict, field_value: Any, field_name: str = None) -> Dict:
        """Update build configuration to add dynamic inputs that can connect to other components."""
        
        if field_name == "form_fields":
            # Clear existing dynamic inputs from build config
            keys_to_remove = [key for key in build_config.keys() if key.startswith("dynamic_")]
            for key in keys_to_remove:
                del build_config[key]
            
            # Add dynamic inputs based on table configuration
            # Safety check to ensure field_value is not None and is iterable
            if field_value is None:
                field_value = []
            
            for i, field_config in enumerate(field_value):
                # Safety check to ensure field_config is not None
                if field_config is None:
                    continue
                    
                field_name = field_config.get("field_name", f"field_{i}")
                display_name = field_config.get("display_name", field_name)
                field_type = field_config.get("field_type", "text").lower()
                default_value = field_config.get("default_value", "")
                required = field_config.get("required", "false").lower() == "true"
                input_types = field_config.get("input_types", "")
                help_text = field_config.get("help_text", "")
                
                # Parse input types for connection capability
                input_types_list = [t.strip() for t in input_types.split(",") if t.strip()] if input_types else []
                
                # Create the appropriate input type based on field_type
                dynamic_input_name = f"dynamic_{field_name}"
                
                if field_type == "text":
                    if input_types_list:
                        build_config[dynamic_input_name] = StrInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=f"{help_text} (Can connect to: {', '.join(input_types_list)})",
                            value=default_value,
                            required=required,
                            input_types=input_types_list,
                        )
                    else:
                        build_config[dynamic_input_name] = StrInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=help_text,
                            value=default_value,
                            required=required,
                        )
                
                elif field_type == "multiline":
                    if input_types_list:
                        build_config[dynamic_input_name] = MultilineInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=f"{help_text} (Can connect to: {', '.join(input_types_list)})",
                            value=default_value,
                            required=required,
                            input_types=input_types_list,
                        )
                    else:
                        build_config[dynamic_input_name] = MultilineInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=help_text,
                            value=default_value,
                            required=required,
                        )
                
                elif field_type == "number":
                    try:
                        default_int = int(default_value) if default_value else 0
                    except ValueError:
                        default_int = 0
                    
                    if input_types_list:
                        build_config[dynamic_input_name] = IntInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=f"{help_text} (Can connect to: {', '.join(input_types_list)})",
                            value=default_int,
                            required=required,
                            input_types=input_types_list,
                        )
                    else:
                        build_config[dynamic_input_name] = IntInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=help_text,
                            value=default_int,
                            required=required,
                        )
                
                elif field_type == "float":
                    try:
                        default_float = float(default_value) if default_value else 0.0
                    except ValueError:
                        default_float = 0.0
                    
                    if input_types_list:
                        build_config[dynamic_input_name] = FloatInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=f"{help_text} (Can connect to: {', '.join(input_types_list)})",
                            value=default_float,
                            required=required,
                            input_types=input_types_list,
                        )
                    else:
                        build_config[dynamic_input_name] = FloatInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=help_text,
                            value=default_float,
                            required=required,
                        )
                
                elif field_type == "boolean":
                    default_bool = default_value.lower() in ["true", "1", "yes"] if default_value else False
                    
                    if input_types_list:
                        build_config[dynamic_input_name] = BoolInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=f"{help_text} (Can connect to: {', '.join(input_types_list)})",
                            value=default_bool,
                            required=required,
                            input_types=input_types_list,
                        )
                    else:
                        build_config[dynamic_input_name] = BoolInput(
                            name=dynamic_input_name,
                            display_name=display_name,
                            info=help_text,
                            value=default_bool,
                            required=required,
                        )
                
                elif field_type == "handle":
                    # HandleInput for generic data connections
                    build_config[dynamic_input_name] = HandleInput(
                        name=dynamic_input_name,
                        display_name=display_name,
                        info=f"{help_text} (Accepts: {', '.join(input_types_list) if input_types_list else 'Any'})",
                        input_types=input_types_list if input_types_list else ["Data", "Text", "Message"],
                        required=required,
                    )
                
                elif field_type == "data":
                    # Specialized for Data type connections
                    build_config[dynamic_input_name] = HandleInput(
                        name=dynamic_input_name,
                        display_name=display_name,
                        info=f"{help_text} (Data input)",
                        input_types=["Data"] if not input_types_list else input_types_list,
                        required=required,
                    )
                
                else:
                    # Default to text input for unknown types
                    build_config[dynamic_input_name] = StrInput(
                        name=dynamic_input_name,
                        display_name=display_name,
                        info=f"{help_text} (Unknown type '{field_type}', defaulting to text)",
                        value=default_value,
                        required=required,
                    )
        
        return build_config

    def get_dynamic_values(self) -> Dict[str, Any]:
        """Extract simple values from all dynamic inputs, handling both manual and connected inputs."""
        dynamic_values = {}
        connection_info = {}
        form_fields = getattr(self, "form_fields", [])
        
        for field_config in form_fields:
            # Safety check to ensure field_config is not None
            if field_config is None:
                continue
                
            field_name = field_config.get("field_name", "")
            if field_name:
                dynamic_input_name = f"dynamic_{field_name}"
                value = getattr(self, dynamic_input_name, None)
                
                # Extract simple values from connections or manual input
                if value is not None:
                    try:
                        extracted_value = self._extract_simple_value(value)
                        dynamic_values[field_name] = extracted_value
                        
                        # Determine connection type for status
                        if hasattr(value, 'text') and hasattr(value, 'timestamp'):
                            connection_info[field_name] = "Connected (Message)"
                        elif hasattr(value, 'data'):
                            connection_info[field_name] = "Connected (Data)"
                        elif isinstance(value, (str, int, float, bool, list, dict)):
                            connection_info[field_name] = "Manual input"
                        else:
                            connection_info[field_name] = "Connected (Object)"
                            
                    except Exception as e:
                        # Fallback to string representation if all else fails
                        dynamic_values[field_name] = str(value)
                        connection_info[field_name] = "Error"
                else:
                    # Use default value if nothing connected
                    default_value = field_config.get("default_value", "")
                    dynamic_values[field_name] = default_value
                    connection_info[field_name] = "Default value"
        
        # Store connection info for status output
        self._connection_info = connection_info
        return dynamic_values
    
    def _extract_simple_value(self, value: Any) -> Any:
        """Extract the simplest, most useful value from any input type."""
        
        # Handle None
        if value is None:
            return None
            
        # Handle simple types directly
        if isinstance(value, (str, int, float, bool)):
            return value
            
        # Handle lists and tuples - keep simple
        if isinstance(value, (list, tuple)):
            return [self._extract_simple_value(item) for item in value]
            
        # Handle dictionaries - keep simple
        if isinstance(value, dict):
            return {str(k): self._extract_simple_value(v) for k, v in value.items()}
            
        # Handle Message objects - extract only the text
        if hasattr(value, 'text'):
            return str(value.text) if value.text is not None else ""
            
        # Handle Data objects - extract the data content
        if hasattr(value, 'data') and value.data is not None:
            return self._extract_simple_value(value.data)
            
        # For any other object, convert to string
        return str(value)
    
    def process_form(self) -> Data:
        """Process all dynamic form inputs and return clean data with just field values."""
        
        # Get all dynamic values (just the key:value pairs)
        dynamic_values = self.get_dynamic_values()
        
        # Update status with connection info
        connected_fields = len([v for v in getattr(self, '_connection_info', {}).values() if 'Connected' in v])
        total_fields = len(dynamic_values)
        
        self.status = f"Form processed successfully. {connected_fields}/{total_fields} fields connected to components."
        
        # Return clean Data object with just the field values
        return Data(data=dynamic_values)


    def get_message(self) -> Message:
        """Return form data as a formatted text message."""
        
        # Get all dynamic values
        dynamic_values = self.get_dynamic_values()
        
        if not dynamic_values:
            return Message(text="No form data available")
        
        # Format as text message
        message_lines = ["📋 Form Data:"]
        message_lines.append("=" * 40)
        
        for field_name, value in dynamic_values.items():
            # Get display name from field config if available
            form_fields = getattr(self, "form_fields", [])
            display_name = field_name
            
            for field_config in form_fields:
                if field_config and field_config.get("field_name") == field_name:
                    display_name = field_config.get("display_name", field_name)
                    break
            
            message_lines.append(f"• {display_name}: {value}")
        
        message_lines.append("=" * 40)
        message_lines.append(f"Total fields: {len(dynamic_values)}")
        
        message_text = "\n".join(message_lines)
        self.status = f"Message formatted with {len(dynamic_values)} fields"
        
        return Message(text=message_text) 