from typing import Any
from pathlib import Path

from lfx.custom import Component
from lfx.io import FileInput, Output
from lfx.schema import Message


class FilePathComponent(Component):
    """Component that generates only the file path from uploaded files.
    
    This component is a simplified version that focuses solely on providing
    the file path without processing the file content.
    """

    display_name = "File Path"
    description = "Generates file paths from uploaded files without processing content."
    icon = "file-text"
    name = "File Path"

    # Supported file extensions
    VALID_EXTENSIONS = [
        "txt", "md", "py", "js", "html", "css", "json", "xml", "csv", 
        "xlsx", "parquet", "pdf", "doc", "docx", "zip", "tar", "gz"
    ]

    inputs = [
        FileInput(
            name="path",
            display_name="Files",
            fileTypes=VALID_EXTENSIONS,
            info=f"Upload files to get their paths. Supported extensions: {', '.join(VALID_EXTENSIONS)}",
            required=True,
            list=True,
            value=[],
        ),
    ]

    outputs = [
        Output(
            display_name="File Path", 
            name="file_paths", 
            method="get_file_paths"
        ),
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically update outputs based on the number of files uploaded."""
        if field_name == "path":
            # Start with empty outputs
            frontend_node["outputs"] = []
            
            if not field_value or len(field_value) == 0:
                # No files uploaded
                frontend_node["outputs"].append(
                    Output(
                        display_name="File Paths", 
                        name="file_paths", 
                        method="get_file_paths"
                    ).to_dict()
                )
            elif len(field_value) == 1:
                # Single file
                frontend_node["outputs"].append(
                    Output(
                        display_name="Single File Path", 
                        name="single_file_path", 
                        method="get_single_file_path"
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="File Paths", 
                        name="file_paths", 
                        method="get_file_paths"
                    ).to_dict()
                )
            else:
                # Multiple files
                frontend_node["outputs"].append(
                    Output(
                        display_name="File Paths", 
                        name="file_paths", 
                        method="get_file_paths"
                    ).to_dict()
                )
                frontend_node["outputs"].append(
                    Output(
                        display_name="File Paths List", 
                        name="file_paths_list", 
                        method="get_file_paths_list"
                    ).to_dict()
                )

        return frontend_node

    def get_file_paths(self) -> Message:
        """Returns a Message containing all file paths separated by newlines."""
        try:
            if not hasattr(self, 'path') or not self.path:
                return Message(text="No files uploaded")
            
            # Extract file paths
            paths = []
            for file_info in self.path:
                if hasattr(file_info, 'file_path'):
                    # Handle FileInfo objects
                    paths.append(file_info.file_path)
                elif isinstance(file_info, str):
                    # Handle string paths
                    paths.append(file_info)
                elif hasattr(file_info, 'path'):
                    # Handle objects with path attribute
                    paths.append(str(file_info.path))
                else:
                    # Fallback
                    paths.append(str(file_info))
            
            if not paths:
                return Message(text="No valid file paths found")
            
            # Join paths with newlines
            paths_text = "\n".join(paths)
            self.status = f"Generated {len(paths)} file path(s)"
            
            return Message(text=paths_text)
            
        except Exception as e:
            error_msg = f"Error getting file paths: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def get_single_file_path(self) -> Message:
        """Returns a Message containing the path of a single file."""
        try:
            if not hasattr(self, 'path') or not self.path or len(self.path) != 1:
                return Message(text="Single file path output requires exactly one file")
            
            file_info = self.path[0]
            
            # Extract single file path
            if hasattr(file_info, 'file_path'):
                file_path = file_info.file_path
            elif isinstance(file_info, str):
                file_path = file_info
            elif hasattr(file_info, 'path'):
                file_path = str(file_info.path)
            else:
                file_path = str(file_info)
            
            self.status = "Generated single file path"
            return Message(text=file_path)
            
        except Exception as e:
            error_msg = f"Error getting single file path: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")

    def get_file_paths_list(self) -> Message:
        """Returns a Message containing file paths as a JSON-like list string."""
        try:
            if not hasattr(self, 'path') or not self.path:
                return Message(text="No files uploaded")
            
            # Extract file paths
            paths = []
            for file_info in self.path:
                if hasattr(file_info, 'file_path'):
                    paths.append(file_info.file_path)
                elif isinstance(file_info, str):
                    paths.append(file_info)
                elif hasattr(file_info, 'path'):
                    paths.append(str(file_info.path))
                else:
                    paths.append(str(file_info))
            
            if not paths:
                return Message(text="No valid file paths found")
            
            # Create a list-like string representation
            paths_list = "[" + ", ".join(f'"{path}"' for path in paths) + "]"
            self.status = f"Generated {len(paths)} file path(s) as list"
            
            return Message(text=paths_list)
            
        except Exception as e:
            error_msg = f"Error getting file paths list: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Message(text=f"Error: {error_msg}")
