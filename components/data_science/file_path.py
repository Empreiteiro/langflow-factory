from copy import deepcopy
from typing import Any

from lfx.base.data.base_file import BaseFileComponent
from lfx.base.data.utils import TEXT_FILE_TYPES
from lfx.io import FileInput, Output
from lfx.schema.data import Data


class FilePathComponent(BaseFileComponent):
    """Extracts file paths from uploaded files."""

    display_name = "File Path Extractor"
    description = "Extracts the file path of uploaded files."
    icon = "file"
    name = "FilePathExtractor"

    VALID_EXTENSIONS = TEXT_FILE_TYPES + ["sqlite"]

    _base_inputs = deepcopy(BaseFileComponent._base_inputs)

    for input_item in _base_inputs:
        if isinstance(input_item, FileInput) and input_item.name == "path":
            input_item.real_time_refresh = True
            break

    inputs = [
        *_base_inputs,
    ]

    outputs = [
        Output(display_name="File Path", name="extracted_path", method="get_file_path"),
    ]

    def process_files(self, file_list):
        """Required abstract method implementation."""
        # For this component, we just need to store the file list
        self.file_list = file_list
        return file_list

    def get_file_path(self) -> Data:
        """Return the file path as text."""
        try:
            if not self.file_list:
                return Data(text="No files provided")
            
            # Get the first file path
            file_path = str(self.file_list[0].path)
            return Data(text=file_path)
            
        except Exception as e:
            error_msg = f"Failed to extract file path: {str(e)}"
            self.log(error_msg)
            return Data(text=error_msg)
