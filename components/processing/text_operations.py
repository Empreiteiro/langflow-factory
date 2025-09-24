import pandas as pd
import re
from typing import Any, List, Dict

from langflow.custom import Component
from langflow.inputs import (
    BoolInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    SortableListInput,
    StrInput,
)
from langflow.io import Output
from langflow.schema.data import Data
from langflow.schema.dataframe import DataFrame
from langflow.schema.message import Message


class TextOperations(Component):
    """Text Operations Component

    This component provides various text processing operations including
    text-to-DataFrame conversion, text analysis, and text transformations.

    ## Features
    - **Text to DataFrame**: Convert formatted text tables to DataFrames
    - **Text Analysis**: Count words, characters, lines, etc.
    - **Text Transformations**: Case conversion, trimming, replacement
    - **Text Filtering**: Filter lines based on conditions
    - **Text Extraction**: Extract specific patterns or sections
    - **Text Formatting**: Format text with various options

    ## Operations Available
    - **Text to DataFrame**: Parse markdown-style tables into DataFrames
    - **Word Count**: Count words, characters, lines in text
    - **Case Conversion**: Convert to uppercase, lowercase, title case
    - **Text Replace**: Replace text patterns with new values
    - **Text Filter**: Filter lines based on conditions
    - **Text Extract**: Extract text matching patterns
    - **Text Format**: Format text with padding, alignment, etc.
    - **Text Split**: Split text into parts based on delimiters
    - **Text Join**: Join text parts with separators
    - **Text Clean**: Remove extra whitespace, special characters
    """

    display_name = "Text Operations"
    description = "Perform various text processing operations including text-to-DataFrame conversion."
    icon = "type"
    name = "TextOperations"

    OPERATION_CHOICES = [
        "Text to DataFrame",
        "Word Count",
        "Case Conversion", 
        "Text Replace",
        "Text Filter",
        "Text Extract",
        "Text Format",
        "Text Split",
        "Text Join",
        "Text Clean",
    ]

    inputs = [
        MessageTextInput(
            name="text_input",
            display_name="Text Input",
            info="The input text to process.",
            required=True,
        ),
        SortableListInput(
            name="operation",
            display_name="Operation",
            placeholder="Select Operation",
            info="Select the text operation to perform.",
            options=[
                {"name": "Text to DataFrame", "icon": "table"},
                {"name": "Word Count", "icon": "hash"},
                {"name": "Case Conversion", "icon": "type"},
                {"name": "Text Replace", "icon": "replace"},
                {"name": "Text Filter", "icon": "filter"},
                {"name": "Text Extract", "icon": "search"},
                {"name": "Text Format", "icon": "align-left"},
                {"name": "Text Split", "icon": "scissors"},
                {"name": "Text Join", "icon": "link"},
                {"name": "Text Clean", "icon": "sparkles"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Text to DataFrame specific inputs
        StrInput(
            name="table_separator",
            display_name="Table Separator",
            info="Separator used in the table (default: '|').",
            value="|",
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="has_header",
            display_name="Has Header",
            info="Whether the table has a header row.",
            value=True,
            dynamic=True,
            show=False,
        ),
        # Word Count specific inputs
        BoolInput(
            name="count_words",
            display_name="Count Words",
            info="Include word count in analysis.",
            value=True,
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="count_characters",
            display_name="Count Characters",
            info="Include character count in analysis.",
            value=True,
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="count_lines",
            display_name="Count Lines",
            info="Include line count in analysis.",
            value=True,
            dynamic=True,
            show=False,
        ),
        # Case Conversion specific inputs
        DropdownInput(
            name="case_type",
            display_name="Case Type",
            options=["uppercase", "lowercase", "title", "capitalize", "swapcase"],
            value="lowercase",
            info="Type of case conversion to apply.",
            dynamic=True,
            show=False,
        ),
        # Text Replace specific inputs
        StrInput(
            name="search_pattern",
            display_name="Search Pattern",
            info="Text pattern to search for (supports regex).",
            dynamic=True,
            show=False,
        ),
        StrInput(
            name="replacement_text",
            display_name="Replacement Text",
            info="Text to replace the search pattern with.",
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="use_regex",
            display_name="Use Regex",
            info="Whether to treat search pattern as regex.",
            value=False,
            dynamic=True,
            show=False,
        ),
        # Text Filter specific inputs
        StrInput(
            name="filter_pattern",
            display_name="Filter Pattern",
            info="Pattern to filter lines by.",
            dynamic=True,
            show=False,
        ),
        DropdownInput(
            name="filter_mode",
            display_name="Filter Mode",
            options=["contains", "starts_with", "ends_with", "equals", "regex"],
            value="contains",
            info="How to apply the filter pattern.",
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="invert_filter",
            display_name="Invert Filter",
            info="Show lines that DON'T match the pattern.",
            value=False,
            dynamic=True,
            show=False,
        ),
        # Text Extract specific inputs
        StrInput(
            name="extract_pattern",
            display_name="Extract Pattern",
            info="Regex pattern to extract from text.",
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="max_matches",
            display_name="Max Matches",
            info="Maximum number of matches to extract.",
            value=10,
            dynamic=True,
            show=False,
        ),
        # Text Format specific inputs
        DropdownInput(
            name="format_type",
            display_name="Format Type",
            options=["pad", "center", "justify", "wrap", "indent"],
            value="pad",
            info="Type of text formatting to apply.",
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="format_width",
            display_name="Format Width",
            info="Width for formatting operations.",
            value=80,
            dynamic=True,
            show=False,
        ),
        StrInput(
            name="format_fill",
            display_name="Format Fill Character",
            info="Character to use for padding/filling.",
            value=" ",
            dynamic=True,
            show=False,
        ),
        # Text Split specific inputs
        StrInput(
            name="split_delimiter",
            display_name="Split Delimiter",
            info="Delimiter to split text by.",
            value=",",
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="max_splits",
            display_name="Max Splits",
            info="Maximum number of splits to perform.",
            value=-1,
            dynamic=True,
            show=False,
        ),
        # Text Join specific inputs
        StrInput(
            name="join_separator",
            display_name="Join Separator",
            info="Separator to join text parts with.",
            value=" ",
            dynamic=True,
            show=False,
        ),
        # Text Clean specific inputs
        BoolInput(
            name="remove_extra_spaces",
            display_name="Remove Extra Spaces",
            info="Remove multiple consecutive spaces.",
            value=True,
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="remove_special_chars",
            display_name="Remove Special Characters",
            info="Remove special characters except alphanumeric and spaces.",
            value=False,
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="remove_empty_lines",
            display_name="Remove Empty Lines",
            info="Remove empty lines from text.",
            value=False,
            dynamic=True,
            show=False,
        ),
    ]

    outputs = [
        Output(display_name="DataFrame", name="dataframe", method="get_dataframe"),
        Output(display_name="Text", name="text", method="get_text"),
        Output(display_name="Data", name="data", method="get_data"),
        Output(display_name="Message", name="message", method="get_message"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._result = None
        self._operation_result = None

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str = None) -> dict:
        """Update build configuration to show/hide relevant inputs based on operation."""
        # Hide all dynamic inputs by default
        dynamic_fields = [
            "table_separator", "has_header",
            "count_words", "count_characters", "count_lines",
            "case_type",
            "search_pattern", "replacement_text", "use_regex",
            "filter_pattern", "filter_mode", "invert_filter",
            "extract_pattern", "max_matches",
            "format_type", "format_width", "format_fill",
            "split_delimiter", "max_splits",
            "join_separator",
            "remove_extra_spaces", "remove_special_chars", "remove_empty_lines",
        ]
        
        for field in dynamic_fields:
            if field in build_config:
                build_config[field]["show"] = False

        if field_name == "operation":
            # Handle SortableListInput format
            if isinstance(field_value, list) and len(field_value) > 0:
                operation_name = field_value[0].get("name", "")
            else:
                operation_name = ""

            # Show relevant inputs based on operation
            if operation_name == "Text to DataFrame":
                build_config["table_separator"]["show"] = True
                build_config["has_header"]["show"] = True
            elif operation_name == "Word Count":
                build_config["count_words"]["show"] = True
                build_config["count_characters"]["show"] = True
                build_config["count_lines"]["show"] = True
            elif operation_name == "Case Conversion":
                build_config["case_type"]["show"] = True
            elif operation_name == "Text Replace":
                build_config["search_pattern"]["show"] = True
                build_config["replacement_text"]["show"] = True
                build_config["use_regex"]["show"] = True
            elif operation_name == "Text Filter":
                build_config["filter_pattern"]["show"] = True
                build_config["filter_mode"]["show"] = True
                build_config["invert_filter"]["show"] = True
            elif operation_name == "Text Extract":
                build_config["extract_pattern"]["show"] = True
                build_config["max_matches"]["show"] = True
            elif operation_name == "Text Format":
                build_config["format_type"]["show"] = True
                build_config["format_width"]["show"] = True
                build_config["format_fill"]["show"] = True
            elif operation_name == "Text Split":
                build_config["split_delimiter"]["show"] = True
                build_config["max_splits"]["show"] = True
            elif operation_name == "Text Join":
                build_config["join_separator"]["show"] = True
            elif operation_name == "Text Clean":
                build_config["remove_extra_spaces"]["show"] = True
                build_config["remove_special_chars"]["show"] = True
                build_config["remove_empty_lines"]["show"] = True

        return build_config

    def get_operation_name(self) -> str:
        """Get the selected operation name."""
        operation_input = getattr(self, "operation", [])
        if isinstance(operation_input, list) and len(operation_input) > 0:
            return operation_input[0].get("name", "")
        return ""

    def process_text(self) -> Any:
        """Process text based on selected operation."""
        text = getattr(self, "text_input", "")
        if not text:
            return None

        operation = self.get_operation_name()
        
        if operation == "Text to DataFrame":
            return self.text_to_dataframe(text)
        elif operation == "Word Count":
            return self.word_count(text)
        elif operation == "Case Conversion":
            return self.case_conversion(text)
        elif operation == "Text Replace":
            return self.text_replace(text)
        elif operation == "Text Filter":
            return self.text_filter(text)
        elif operation == "Text Extract":
            return self.text_extract(text)
        elif operation == "Text Format":
            return self.text_format(text)
        elif operation == "Text Split":
            return self.text_split(text)
        elif operation == "Text Join":
            return self.text_join(text)
        elif operation == "Text Clean":
            return self.text_clean(text)
        else:
            return text

    def text_to_dataframe(self, text: str) -> DataFrame:
        """Convert markdown-style table text to DataFrame."""
        try:
            lines = text.strip().split('\n')
            if not lines:
                return DataFrame(pd.DataFrame())
            
            # Remove empty lines
            lines = [line.strip() for line in lines if line.strip()]
            
            separator = getattr(self, "table_separator", "|")
            has_header = getattr(self, "has_header", True)
            
            # Parse table rows
            rows = []
            for line in lines:
                # Remove leading/trailing separators and split
                if line.startswith(separator):
                    line = line[1:]
                if line.endswith(separator):
                    line = line[:-1]
                
                # Split by separator and clean up
                cells = [cell.strip() for cell in line.split(separator)]
                rows.append(cells)
            
            if not rows:
                return DataFrame(pd.DataFrame())
            
            # Create DataFrame
            if has_header and len(rows) > 1:
                # Use first row as header
                df = pd.DataFrame(rows[1:], columns=rows[0])
            else:
                # No header, use generic column names
                max_cols = max(len(row) for row in rows) if rows else 0
                columns = [f"col_{i}" for i in range(max_cols)]
                df = pd.DataFrame(rows, columns=columns)
            
            # Try to convert numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            
            self._result = df
            self.log(f"Successfully converted text to DataFrame with {len(df)} rows and {len(df.columns)} columns")
            return DataFrame(df)
            
        except Exception as e:
            self.log(f"Error converting text to DataFrame: {str(e)}")
            return DataFrame(pd.DataFrame({"error": [str(e)]}))

    def word_count(self, text: str) -> Dict[str, Any]:
        """Count words, characters, and lines in text."""
        try:
            result = {}
            
            if getattr(self, "count_words", True):
                words = text.split()
                result["word_count"] = len(words)
                result["unique_words"] = len(set(words))
            
            if getattr(self, "count_characters", True):
                result["character_count"] = len(text)
                result["character_count_no_spaces"] = len(text.replace(" ", ""))
            
            if getattr(self, "count_lines", True):
                lines = text.split('\n')
                result["line_count"] = len(lines)
                result["non_empty_lines"] = len([line for line in lines if line.strip()])
            
            self._result = result
            self.log(f"Text analysis completed: {result}")
            return result
            
        except Exception as e:
            self.log(f"Error analyzing text: {str(e)}")
            return {}

    def case_conversion(self, text: str) -> str:
        """Convert text case."""
        try:
            case_type = getattr(self, "case_type", "lowercase")
            
            if case_type == "uppercase":
                result = text.upper()
            elif case_type == "lowercase":
                result = text.lower()
            elif case_type == "title":
                result = text.title()
            elif case_type == "capitalize":
                result = text.capitalize()
            elif case_type == "swapcase":
                result = text.swapcase()
            else:
                result = text
            
            self._result = result
            self.log(f"Text converted to {case_type}")
            return result
            
        except Exception as e:
            self.log(f"Error converting case: {str(e)}")
            return text

    def text_replace(self, text: str) -> str:
        """Replace text patterns."""
        try:
            search_pattern = getattr(self, "search_pattern", "")
            replacement_text = getattr(self, "replacement_text", "")
            use_regex = getattr(self, "use_regex", False)
            
            if not search_pattern:
                return text
            
            if use_regex:
                result = re.sub(search_pattern, replacement_text, text)
            else:
                result = text.replace(search_pattern, replacement_text)
            
            self._result = result
            self.log(f"Text replacement completed")
            return result
            
        except Exception as e:
            self.log(f"Error replacing text: {str(e)}")
            return text

    def text_filter(self, text: str) -> str:
        """Filter lines based on pattern."""
        try:
            filter_pattern = getattr(self, "filter_pattern", "")
            filter_mode = getattr(self, "filter_mode", "contains")
            invert_filter = getattr(self, "invert_filter", False)
            
            if not filter_pattern:
                return text
            
            lines = text.split('\n')
            filtered_lines = []
            
            for line in lines:
                match = False
                
                if filter_mode == "contains":
                    match = filter_pattern in line
                elif filter_mode == "starts_with":
                    match = line.startswith(filter_pattern)
                elif filter_mode == "ends_with":
                    match = line.endswith(filter_pattern)
                elif filter_mode == "equals":
                    match = line.strip() == filter_pattern
                elif filter_mode == "regex":
                    match = bool(re.search(filter_pattern, line))
                
                if invert_filter:
                    match = not match
                
                if match:
                    filtered_lines.append(line)
            
            result = '\n'.join(filtered_lines)
            self._result = result
            self.log(f"Text filtered: {len(filtered_lines)} lines remaining")
            return result
            
        except Exception as e:
            self.log(f"Error filtering text: {str(e)}")
            return text

    def text_extract(self, text: str) -> List[str]:
        """Extract text matching patterns."""
        try:
            extract_pattern = getattr(self, "extract_pattern", "")
            max_matches = getattr(self, "max_matches", 10)
            
            if not extract_pattern:
                return []
            
            matches = re.findall(extract_pattern, text)
            if max_matches > 0:
                matches = matches[:max_matches]
            
            self._result = matches
            self.log(f"Extracted {len(matches)} matches")
            return matches
            
        except Exception as e:
            self.log(f"Error extracting text: {str(e)}")
            return []

    def text_format(self, text: str) -> str:
        """Format text with various options."""
        try:
            format_type = getattr(self, "format_type", "pad")
            format_width = getattr(self, "format_width", 80)
            format_fill = getattr(self, "format_fill", " ")
            
            if format_type == "pad":
                result = text.ljust(format_width, format_fill)
            elif format_type == "center":
                result = text.center(format_width, format_fill)
            elif format_type == "justify":
                # Simple justification by adding spaces
                words = text.split()
                if len(words) > 1:
                    total_spaces = format_width - len(text.replace(" ", ""))
                    spaces_per_gap = total_spaces // (len(words) - 1)
                    extra_spaces = total_spaces % (len(words) - 1)
                    result = words[0]
                    for i, word in enumerate(words[1:], 1):
                        spaces = spaces_per_gap + (1 if i <= extra_spaces else 0)
                        result += " " * spaces + word
                else:
                    result = text
            elif format_type == "wrap":
                import textwrap
                result = textwrap.fill(text, width=format_width)
            elif format_type == "indent":
                indent = format_fill * format_width
                result = '\n'.join(indent + line for line in text.split('\n'))
            else:
                result = text
            
            self._result = result
            self.log(f"Text formatted with {format_type}")
            return result
            
        except Exception as e:
            self.log(f"Error formatting text: {str(e)}")
            return text

    def text_split(self, text: str) -> List[str]:
        """Split text by delimiter."""
        try:
            split_delimiter = getattr(self, "split_delimiter", ",")
            max_splits = getattr(self, "max_splits", -1)
            
            if max_splits > 0:
                result = text.split(split_delimiter, max_splits)
            else:
                result = text.split(split_delimiter)
            
            # Clean up whitespace
            result = [part.strip() for part in result]
            
            self._result = result
            self.log(f"Text split into {len(result)} parts")
            return result
            
        except Exception as e:
            self.log(f"Error splitting text: {str(e)}")
            return [text]

    def text_join(self, text: str) -> str:
        """Join text parts with separator."""
        try:
            join_separator = getattr(self, "join_separator", " ")
            
            # Split by common delimiters first
            lines = text.split('\n')
            parts = []
            for line in lines:
                if ',' in line:
                    parts.extend(line.split(','))
                elif ';' in line:
                    parts.extend(line.split(';'))
                elif '|' in line:
                    parts.extend(line.split('|'))
                else:
                    parts.append(line)
            
            # Clean up and join
            parts = [part.strip() for part in parts if part.strip()]
            result = join_separator.join(parts)
            
            self._result = result
            self.log(f"Text joined with '{join_separator}'")
            return result
            
        except Exception as e:
            self.log(f"Error joining text: {str(e)}")
            return text

    def text_clean(self, text: str) -> str:
        """Clean text by removing extra spaces, special chars, etc."""
        try:
            result = text
            
            if getattr(self, "remove_extra_spaces", True):
                # Replace multiple spaces with single space
                result = re.sub(r'\s+', ' ', result)
            
            if getattr(self, "remove_special_chars", False):
                # Keep only alphanumeric, spaces, and basic punctuation
                result = re.sub(r'[^\w\s.,!?;:-]', '', result)
            
            if getattr(self, "remove_empty_lines", False):
                # Remove empty lines
                lines = result.split('\n')
                lines = [line for line in lines if line.strip()]
                result = '\n'.join(lines)
            
            self._result = result
            self.log("Text cleaned successfully")
            return result
            
        except Exception as e:
            self.log(f"Error cleaning text: {str(e)}")
            return text

    def get_dataframe(self) -> DataFrame:
        """Return result as DataFrame if applicable."""
        operation = self.get_operation_name()
        
        # For Text to DataFrame operation, process the text directly
        if operation == "Text to DataFrame":
            text = getattr(self, "text_input", "")
            if text:
                return self.text_to_dataframe(text)
            return DataFrame(pd.DataFrame())
        
        # For other operations, use stored result
        if self._result is not None:
            if isinstance(self._result, dict):
                df = pd.DataFrame([self._result])
            elif isinstance(self._result, list):
                df = pd.DataFrame({"result": self._result})
            else:
                df = pd.DataFrame({"result": [str(self._result)]})
            self.log(f"Returning DataFrame with {len(df)} rows and columns: {list(df.columns)}")
            return DataFrame(df)
        return DataFrame(pd.DataFrame())

    def get_text(self) -> str:
        """Return result as text."""
        if self._result is not None:
            if isinstance(self._result, list):
                return '\n'.join(str(item) for item in self._result)
            elif isinstance(self._result, dict):
                return '\n'.join(f"{k}: {v}" for k, v in self._result.items())
            else:
                return str(self._result)
        return ""

    def get_data(self) -> Data:
        """Return result as Data object."""
        result = self.process_text()
        if result is not None:
            if isinstance(result, dict):
                return Data(data=result)
            elif isinstance(result, list):
                return Data(data={"items": result})
            else:
                return Data(data={"result": str(result)})
        return Data(data={})

    def get_message(self) -> Message:
        """Return result as formatted message."""
        operation = self.get_operation_name()
        result = self.process_text()
        
        if result is not None:
            if operation == "Word Count" and isinstance(result, dict):
                message_lines = ["📊 Text Analysis Results:"]
                message_lines.append("=" * 30)
                for key, value in result.items():
                    message_lines.append(f"• {key.replace('_', ' ').title()}: {value}")
            elif isinstance(result, list):
                message_lines = [f"📋 {operation} Results:"]
                message_lines.append("=" * 30)
                for i, item in enumerate(result, 1):
                    message_lines.append(f"{i}. {item}")
            else:
                message_lines = [f"📝 {operation} Result:"]
                message_lines.append("=" * 30)
                message_lines.append(str(result))
        else:
            message_lines = ["❌ No result available"]
        
        message_text = '\n'.join(message_lines)
        return Message(text=message_text)
