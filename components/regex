import re
from langflow.custom import Component
from langflow.io import DataInput, StrInput, Output
from langflow.schema import Data
from langflow.schema.message import Message


class RegexExtractorComponent(Component):
    display_name = "Regex Extractor"
    description = "Extracts parts of the input data using a regular expression."
    icon = "search"
    name = "RegexExtractor"

    inputs = [
        DataInput(
            name="data",
            display_name="Data",
            info="The data from which to extract information.",
            is_list=False,
            required=True
        ),
        StrInput(
            name="regex_pattern",
            display_name="Regex Pattern",
            info="The regex pattern to use for extraction.",
            value="phone.*?(\\d+)",
            required=True,
        )
    ]

    outputs = [
        Output(
            display_name="Extracted Text",
            name="text",
            info="Extracted text as a single concatenated string.",
            method="extract_text",
        )
    ]

    def extract_text(self) -> Message:
        """Extract text using the provided regex pattern."""
        payload = self.data.data  # Assumindo que o payload é um dict no campo data
        regex_pattern = self.regex_pattern
        
        # Converte o payload para string para aplicar o regex
        payload_str = str(payload)
        self.log(f"Payload como string: {payload_str}")
        
        # Aplica o regex e junta os resultados
        matches = re.findall(regex_pattern, payload_str)
        self.log(f"Matches encontrados: {matches}")
        
        if matches:
            result_string = " | ".join(matches)
        else:
            result_string = "Nenhum resultado encontrado"
        
        self.status = result_string
        return Message(text=result_string)
