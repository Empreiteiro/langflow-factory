from langflow.custom import Component
from langflow.io import BoolInput, DropdownInput, MessageInput, MessageTextInput, Output, HandleInput, TabInput, TableInput
from langflow.schema.message import Message
from langchain_core.language_models import BaseLanguageModel
import re
from typing import Any


class BackupConditionalRouterComponent(Component):
    display_name = "Conditional Router"
    description = "Routes an input message to a corresponding output based on text comparison or LLM-based categorization."
    icon = "equal"
    name = "BackupConditionalRouter"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._categorization_result = None

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="The primary text input for the operation.",
        ),
        TabInput(
            name="mode",
            display_name="Mode",
            options=["Text Comparison", "Categorization"],
            value="Text Comparison",
            info="Select between direct comparison and LLM-based categorization.",
            real_time_refresh=True,
        ),
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="LLM to use for categorization.",
            input_types=["LanguageModel"],
            required=False,
            dynamic=True,
            show=False,
        ),
        DropdownInput(
            name="operator",
            display_name="Operator",
            options=["equals", "not equals", "contains", "starts with", "ends with", "regex"],
            info="The operator to apply for comparing the texts.",
            value="equals",
            real_time_refresh=True,
        ),
        TableInput(
            name="cases",
            display_name="Cases",
            info="Define the cases for routing. Each row should have a label and a value.",
            table_schema=[
                {"name": "label", "display_name": "Label", "type": "str", "description": "Case label (used for output name)"},
                {"name": "value", "display_name": "Value", "type": "str", "description": "Text or category to match"},
            ],
            value=[{"label": "Case 1", "value": ""}, {"label": "Case 2", "value": ""}],
            real_time_refresh=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name="Case Sensitive",
            info="If true, the comparison will be case sensitive.",
            value=False,
            advanced=True,
            dynamic=True,
            show=True,
        ),
        MessageInput(
            name="message",
            display_name="Message",
            info="The message to pass through either route.",
        ),
    ]

    outputs = [
        Output(display_name="Else", name="default_result", method="default_response", group_outputs=True),
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Create a dynamic output for each case in the cases table."""
        if field_name == "cases":
            frontend_node["outputs"] = []
            
            # Add a dynamic output for each case - all using the same method
            for i, row in enumerate(field_value):
                label = row.get("label", f"Case {i+1}")
                frontend_node["outputs"].append(
                    Output(
                        display_name=label,
                        name=f"case_{i+1}_result",
                        method="process_case",
                        group_outputs=f"True"
                    )
                )
            # Always add a default output
            frontend_node["outputs"].append(
                Output(display_name="Else", name="default_result", method="default_response", group_outputs=True)
            )
        return frontend_node

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "mode":
            build_config["llm"]["show"] = field_value == "Categorization"
            build_config["case_sensitive"]["show"] = field_value == "Text Comparison"
            build_config["operator"]["show"] = field_value == "Text Comparison"
        return build_config

    def evaluate_condition(self, input_text: str, match_text: str, operator: str, case_sensitive: bool) -> bool:
        if not case_sensitive:
            input_text = input_text.lower()
            match_text = match_text.lower()
        
        conditions = {
            "equals": input_text == match_text,
            "not equals": input_text != match_text,
            "contains": match_text in input_text,
            "starts with": input_text.startswith(match_text),
            "ends with": input_text.endswith(match_text),
        }
        return conditions.get(operator, False)

    def process_case(self) -> Message:
        """Process all cases and return message for matching case, stop others."""
        cases = getattr(self, "cases", [])
        input_text = getattr(self, "input_text", "")
        mode = getattr(self, "mode", "Text Comparison")
        operator = getattr(self, "operator", "equals")
        case_sensitive = getattr(self, "case_sensitive", False)
        message = getattr(self, "message", Message(text=""))
        
        # Find the matching case
        matched_case = None
        
        if mode == "Text Comparison":
            # Direct text comparison
            for i, case in enumerate(cases):
                match_value = case.get("value", "")
                if match_value and self.evaluate_condition(input_text, match_value, operator, case_sensitive):
                    matched_case = i
                    break
        
        elif mode == "Categorization":
            # LLM-based categorization
            llm = getattr(self, "llm", None)
            if llm and cases:
                # Create prompt for categorization
                categories = [case.get("value", case.get("label", f"Case {i+1}")) for i, case in enumerate(cases)]
                categories_text = ", ".join([f'"{cat}"' for cat in categories if cat])
                
                prompt = f"""You are a text classifier. Given the following text and categories, determine which category best matches the text.

Text to classify: "{input_text}"

Available categories: {categories_text}

Respond with ONLY the exact category name that best matches the text. If none match well, respond with "NONE".

Category:"""
                
                try:
                    # Use the LLM to categorize
                    if hasattr(llm, 'invoke'):
                        response = llm.invoke(prompt)
                        if hasattr(response, 'content'):
                            categorization = response.content.strip().strip('"')
                        else:
                            categorization = str(response).strip().strip('"')
                    else:
                        categorization = str(llm(prompt)).strip().strip('"')
                    
                    # Find matching case based on LLM response
                    for i, case in enumerate(cases):
                        case_value = case.get("value", "")
                        case_label = case.get("label", "")
                        if (categorization.lower() == case_value.lower() or 
                            categorization.lower() == case_label.lower()):
                            matched_case = i
                            break
                    
                    self.status = f"LLM categorized as: {categorization}"
                    
                except Exception as e:
                    self.status = f"Error in LLM categorization: {str(e)}"
            else:
                self.status = "No LLM provided for categorization"
        
        if matched_case is not None:
            # Stop all case outputs except the matched one
            for i in range(len(cases)):
                if i != matched_case:
                    self.stop(f"case_{i+1}_result")
            
            # Also stop the default output
            self.stop("default_result")
            
            label = cases[matched_case].get("label", f"Case {matched_case+1}")
            if mode == "Text Comparison":
                self.status = f"Matched {label}"
            else:
                self.status = f"Categorized as {label}"
            return message
        else:
            # No match found, stop all case outputs
            for i in range(len(cases)):
                self.stop(f"case_{i+1}_result")
            
            # The default_response will handle the else case
            self.stop("process_case")
            return Message(text="")

    def default_response(self) -> Message:
        """Handle the else case when no conditions match."""
        cases = getattr(self, "cases", [])
        input_text = getattr(self, "input_text", "")
        mode = getattr(self, "mode", "Text Comparison")
        operator = getattr(self, "operator", "equals")
        case_sensitive = getattr(self, "case_sensitive", False)
        message = getattr(self, "message", Message(text=""))
        
        # Check if any case matches based on the mode
        has_match = False
        
        if mode == "Text Comparison":
            for case in cases:
                match_value = case.get("value", "")
                if match_value and self.evaluate_condition(input_text, match_value, operator, case_sensitive):
                    has_match = True
                    break
        
        elif mode == "Categorization":
            llm = getattr(self, "llm", None)
            if llm and cases:
                try:
                    # Create prompt for categorization
                    categories = [case.get("value", case.get("label", f"Case {i+1}")) for i, case in enumerate(cases)]
                    categories_text = ", ".join([f'"{cat}"' for cat in categories if cat])
                    
                    prompt = f"""You are a text classifier. Given the following text and categories, determine which category best matches the text.

Text to classify: "{input_text}"

Available categories: {categories_text}

Respond with ONLY the exact category name that best matches the text. If none match well, respond with "NONE".

Category:"""
                    
                    # Use the LLM to categorize
                    if hasattr(llm, 'invoke'):
                        response = llm.invoke(prompt)
                        if hasattr(response, 'content'):
                            categorization = response.content.strip().strip('"')
                        else:
                            categorization = str(response).strip().strip('"')
                    else:
                        categorization = str(llm(prompt)).strip().strip('"')
                    
                    # Check if LLM response matches any case
                    for case in cases:
                        case_value = case.get("value", "")
                        case_label = case.get("label", "")
                        if (categorization.lower() == case_value.lower() or 
                            categorization.lower() == case_label.lower()):
                            has_match = True
                            break
                
                except Exception:
                    pass  # If there's an error, treat as no match
        
        if has_match:
            # A case matches, stop this output
            self.stop("default_result")
            return Message(text="")
        
        # No case matches, return the message
        self.status = "Routed to Else (no match)"
        return message
