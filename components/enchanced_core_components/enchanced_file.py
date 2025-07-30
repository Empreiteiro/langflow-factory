from copy import deepcopy
from typing import Any

from langflow.base.data.base_file import BaseFileComponent
from langflow.base.data.utils import TEXT_FILE_TYPES, parallel_load_data, parse_text_file_to_data
from langflow.io import BoolInput, FileInput, IntInput, DropdownInput, Output, StrInput, MessageTextInput
from langflow.schema.data import Data
from langflow.schema import DataFrame


class EnhancedFileV2Component(BaseFileComponent):
    """Enhanced file component v2 that combines standard file loading with optional Docling processing and export.

    This component supports all features of the standard File component, plus an advanced mode
    that enables Docling document processing and export to various formats (Markdown, HTML, etc.).
    """

    display_name = "File"
    description = "Loads content from files with optional advanced document processing and export using Docling."
    documentation: str = "https://docs.langflow.org/components-data#file"
    icon = "file-text"
    name = "ile"

    # Docling supported formats from original component
    VALID_EXTENSIONS = [
        "adoc",
        "asciidoc",
        "asc",
        "bmp",
        "csv",
        "dotx",
        "dotm",
        "docm",
        "docx",
        "htm",
        "html",
        "jpeg",
        "json",
        "md",
        "pdf",
        "png",
        "potx",
        "ppsx",
        "pptm",
        "potm",
        "ppsm",
        "pptx",
        "tiff",
        "txt",
        "xls",
        "xlsx",
        "xhtml",
        "xml",
        "webp",
    ] + TEXT_FILE_TYPES

    # Fixed export settings
    EXPORT_FORMAT = "Markdown"
    IMAGE_MODE = "placeholder"

    _base_inputs = deepcopy(BaseFileComponent._base_inputs)

    for input_item in _base_inputs:
        if isinstance(input_item, FileInput) and input_item.name == "path":
            input_item.real_time_refresh = True
            break

    inputs = [
        *_base_inputs,
        BoolInput(
            name="advanced_mode",
            display_name="Advanced Parser",
            value=False,
            real_time_refresh=True,
            info="Enable advanced document processing and export with Docling for PDFs, images, and office documents. Available only for single file processing. Requires installation: uv pip install docling",
            show=False,
        ),
        DropdownInput(
            name="pipeline",
            display_name="Pipeline",
            info="Docling pipeline to use",
            options=["standard", "vlm"],
            value="standard",
            advanced=True,
        ),
        DropdownInput(
            name="ocr_engine",
            display_name="Ocr",
            info="OCR engine to use. Only available when pipeline is set to 'standard'.",
            options=["", "easyocr", "tesserocr", "rapidocr", "ocrmac"],
            value="",
            advanced=True,
        ),

        StrInput(
            name="md_image_placeholder",
            display_name="Image placeholder",
            info="Specify the image placeholder for markdown exports.",
            value="<!-- image -->",
            advanced=True,
            show=False,
        ),
        StrInput(
            name="md_page_break_placeholder",
            display_name="Page break placeholder",
            info="Add this placeholder between pages in the markdown output.",
            value="",
            advanced=True,
            show=False,
        ),
        MessageTextInput(
            name="doc_key",
            display_name="Doc Key",
            info="The key to use for the DoclingDocument column.",
            value="doc",
            advanced=True,
            show=False,
        ),
        BoolInput(
            name="use_multithreading",
            display_name="[Deprecated] Use Multithreading",
            advanced=True,
            value=True,
            info="Set 'Processing Concurrency' greater than 1 to enable multithreading.",
        ),
        IntInput(
            name="concurrency_multithreading",
            display_name="Processing Concurrency",
            advanced=True,
            info="When multiple files are being processed, the number of files to process concurrently.",
            value=1,
        ),
    ]

    outputs = [
        *BaseFileComponent._base_outputs,
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update build configuration to show/hide fields based on file count and advanced_mode."""
        if field_name == "path":
            # Show/hide Advanced Parser based on file count (only for single files)
            file_count = len(field_value) if field_value else 0
            if file_count == 1:
                build_config["advanced_mode"]["show"] = True
            else:
                build_config["advanced_mode"]["show"] = False
                build_config["advanced_mode"]["value"] = False  # Reset to False when hidden
                
                # Hide all advanced fields when Advanced Parser is not available
                advanced_fields = ["pipeline", "ocr_engine", "doc_key", "md_image_placeholder", "md_page_break_placeholder"]
                for field in advanced_fields:
                    if field in build_config:
                        build_config[field]["show"] = False
        
        elif field_name == "advanced_mode":
            # Show/hide advanced fields based on advanced_mode (only if single file)
            advanced_fields = ["pipeline", "ocr_engine", "doc_key", "md_image_placeholder", "md_page_break_placeholder"]
            
            for field in advanced_fields:
                if field in build_config:
                    build_config[field]["show"] = field_value

        return build_config

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically show outputs based on the number of files and their types."""
        if field_name in ["path", "advanced_mode"]:
            # Get current path value
            if field_name == "path":
                path_value = field_value
            else:
                # Get path from frontend_node when advanced_mode changes
                path_value = frontend_node.get("template", {}).get("path", {}).get("file_path", [])
            
            # Add outputs based on the number of files in the path
            if len(path_value) == 0:
                return frontend_node

            # Clear existing outputs
            frontend_node["outputs"] = []

            if len(path_value) == 1:
                # We need to check if the file is structured content
                file_path = path_value[0] if field_name == "path" else frontend_node["template"]["path"]["file_path"][0]
                if file_path.endswith((".csv", ".xlsx", ".parquet")):
                    frontend_node["outputs"].append(
                        Output(display_name="Structured Content", name="dataframe", method="load_files_structured"),
                    )
                elif file_path.endswith(".json"):
                    frontend_node["outputs"].append(
                        Output(display_name="Structured Content", name="json", method="load_files_json"),
                    )

                # Add outputs based on advanced mode
                advanced_mode = frontend_node.get("template", {}).get("advanced_mode", {}).get("value", False)
                
                if advanced_mode:
                    # Advanced mode: Structured Output, Markdown, and File Path
                    frontend_node["outputs"].append(
                        Output(display_name="Structured Output", name="advanced", method="load_files_advanced"),
                    )
                    frontend_node["outputs"].append(
                        Output(display_name="Markdown", name="markdown", method="load_files_message"),
                    )
                    frontend_node["outputs"].append(
                        Output(display_name="File Path", name="path", method="load_files_path"),
                    )
                else:
                    # Normal mode: Raw Content and File Path
                    frontend_node["outputs"].append(
                        Output(display_name="Raw Content", name="message", method="load_files_message"),
                    )
                    frontend_node["outputs"].append(
                        Output(display_name="File Path", name="path", method="load_files_path"),
                    )
            else:
                # For multiple files, we show the files output (DataFrame format)
                # Advanced Parser is not available for multiple files
                frontend_node["outputs"].append(
                    Output(display_name="Files", name="dataframe", method="load_files"),
                )

        return frontend_node

    def _try_import_docling(self):
        """Try different import strategies for docling components."""
        imports = {}
        
        # Try strategy 1: Latest docling structure
        try:
            from docling.datamodel.base_models import ConversionStatus, InputFormat
            from docling.document_converter import DocumentConverter
            from docling_core.types.doc import ImageRefMode
            imports['ConversionStatus'] = ConversionStatus
            imports['InputFormat'] = InputFormat
            imports['DocumentConverter'] = DocumentConverter
            imports['ImageRefMode'] = ImageRefMode
            imports['strategy'] = 'latest'
            self.log("Using latest docling import structure")
            return imports
        except ImportError as e:
            self.log(f"Latest docling structure failed: {e}")
        
        # Try strategy 2: Alternative import paths
        try:
            from docling.document_converter import DocumentConverter
            from docling_core.types.doc import ImageRefMode
            
            # Try to get ConversionStatus from different locations
            ConversionStatus = None
            InputFormat = None
            
            try:
                from docling_core.types import ConversionStatus, InputFormat
            except ImportError:
                try:
                    from docling.datamodel import ConversionStatus, InputFormat
                except ImportError:
                    # Create mock enums if we can't find them
                    from enum import Enum
                    class ConversionStatus(Enum):
                        SUCCESS = "success"
                        FAILURE = "failure"
                    class InputFormat(Enum):
                        PDF = "pdf"
                        IMAGE = "image"
            
            imports['ConversionStatus'] = ConversionStatus
            imports['InputFormat'] = InputFormat
            imports['DocumentConverter'] = DocumentConverter
            imports['ImageRefMode'] = ImageRefMode
            imports['strategy'] = 'alternative'
            self.log("Using alternative docling import structure")
            return imports
        except ImportError as e:
            self.log(f"Alternative docling structure failed: {e}")
        
        # Try strategy 3: Basic converter only
        try:
            from docling.document_converter import DocumentConverter
            
            # Create minimal mock classes
            class ConversionStatus:
                SUCCESS = "success"
                FAILURE = "failure"
            
            class InputFormat:
                PDF = "pdf"
                IMAGE = "image"
                
            class ImageRefMode:
                PLACEHOLDER = "placeholder"
                EMBEDDED = "embedded"
                
            imports['ConversionStatus'] = ConversionStatus
            imports['InputFormat'] = InputFormat
            imports['DocumentConverter'] = DocumentConverter
            imports['ImageRefMode'] = ImageRefMode
            imports['strategy'] = 'basic'
            self.log("Using basic docling import structure with mocks")
            return imports
        except ImportError as e:
            self.log(f"Basic docling structure failed: {e}")
        
        # Strategy 4: Complete fallback - return None to indicate failure
        return None

    def _create_advanced_converter(self, docling_imports):
        """Create advanced converter with pipeline options if available."""
        try:
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption
            
            DocumentConverter = docling_imports['DocumentConverter']
            InputFormat = docling_imports['InputFormat']
            
            # Create basic pipeline options
            pipeline_options = PdfPipelineOptions()
            
            # Configure OCR if specified and available
            if self.ocr_engine:
                try:
                    from docling.models.factories import get_ocr_factory
                    from docling.datamodel.pipeline_options import OcrOptions
                    
                    pipeline_options.do_ocr = True
                    ocr_factory = get_ocr_factory(allow_external_plugins=False)
                    ocr_options = ocr_factory.create_options(kind=self.ocr_engine)
                    pipeline_options.ocr_options = ocr_options
                    self.log(f"Configured OCR with engine: {self.ocr_engine}")
                except Exception as e:
                    self.log(f"Could not configure OCR: {e}, proceeding without OCR")
                    pipeline_options.do_ocr = False
            
            # Create format options
            pdf_format_option = PdfFormatOption(pipeline_options=pipeline_options)
            format_options = {
                InputFormat.PDF: pdf_format_option,
                InputFormat.IMAGE: pdf_format_option,
            }
            
            return DocumentConverter(format_options=format_options)
            
        except Exception as e:
            self.log(f"Could not create advanced converter: {e}, using basic converter")
            return docling_imports['DocumentConverter']()

    def _is_docling_compatible(self, file_path: str) -> bool:
        """Check if file is compatible with Docling processing."""
        # All VALID_EXTENSIONS are Docling compatible (except for TEXT_FILE_TYPES which may overlap)
        docling_extensions = [
            '.adoc', '.asciidoc', '.asc', '.bmp', '.csv', '.dotx', '.dotm', '.docm', '.docx',
            '.htm', '.html', '.jpeg', '.json', '.md', '.pdf', '.png', '.potx', '.ppsx', 
            '.pptm', '.potm', '.ppsm', '.pptx', '.tiff', '.txt', '.xls', '.xlsx', 
            '.xhtml', '.xml', '.webp'
        ]
        return any(file_path.lower().endswith(ext) for ext in docling_extensions)

    def process_files(self, file_list: list[BaseFileComponent.BaseFile]) -> list[BaseFileComponent.BaseFile]:
        """Processes files using standard parsing or Docling based on advanced_mode and file type."""

        def process_file_standard(file_path: str, *, silent_errors: bool = False) -> Data | None:
            """Processes a single file using standard text parsing."""
            try:
                return parse_text_file_to_data(file_path, silent_errors=silent_errors)
            except FileNotFoundError as e:
                msg = f"File not found: {file_path}. Error: {e}"
                self.log(msg)
                if not silent_errors:
                    raise
                return None
            except Exception as e:
                msg = f"Unexpected error processing {file_path}: {e}"
                self.log(msg)
                if not silent_errors:
                    raise
                return None

        def process_file_docling(file_path: str, *, silent_errors: bool = False) -> Data | None:
            """Processes a single file using Docling if compatible, otherwise standard processing."""
            # Try Docling first if file is compatible and advanced mode is enabled
            if self.advanced_mode and self._is_docling_compatible(file_path):
                try:
                    return self._process_with_docling_and_export(file_path)
                except Exception as e:
                    self.log(f"Docling processing failed for {file_path}: {e}, falling back to standard processing")
                    if not silent_errors:
                        # Return error data instead of raising
                        return Data(data={"error": f"Docling processing failed: {e}", "file_path": file_path})
            
            # Fallback to standard processing
            return process_file_standard(file_path, silent_errors=silent_errors)

        if not file_list:
            msg = "No files to process."
            raise ValueError(msg)

        concurrency = 1 if not self.use_multithreading else max(1, self.concurrency_multithreading)
        file_count = len(file_list)

        parallel_processing_threshold = 2
        if concurrency < parallel_processing_threshold or file_count < parallel_processing_threshold:
            if file_count > 1:
                self.log(f"Processing {file_count} files sequentially.")
            processed_data = [process_file_docling(str(file.path), silent_errors=self.silent_errors) for file in file_list]
        else:
            self.log(f"Starting parallel processing of {file_count} files with concurrency: {concurrency}.")
            file_paths = [str(file.path) for file in file_list]
            processed_data = parallel_load_data(
                file_paths,
                silent_errors=self.silent_errors,
                load_function=process_file_docling,
                max_concurrency=concurrency,
            )

        return self.rollup_data(file_list, processed_data)

    def load_files_advanced(self) -> DataFrame:
        """Load files using advanced Docling processing and export to Markdown format."""
        if not self.advanced_mode:
            # Fallback to standard processing if advanced mode is disabled
            return self.load_files()
        
        try:
            resolved_files = self.resolve_path()
            processed_files = self.process_files(resolved_files)
            
            # Extract exported content and create Data objects like Export Docling Document
            results: list[Data] = []
            for file_obj in processed_files:
                if hasattr(file_obj, 'data') and file_obj.data:
                    file_data = file_obj.data.data if hasattr(file_obj.data, 'data') else file_obj.data
                    
                    # Get exported content if available
                    if isinstance(file_data, dict) and 'exported_content' in file_data:
                        # This file was processed with Docling
                        exported_content = file_data['exported_content']
                        results.append(Data(
                            text=exported_content,
                            data={
                                "file_path": file_data.get("file_path", ""),
                                "export_format": file_data.get("export_format", "Markdown")
                            }
                        ))
                    else:
                        # This file was processed with standard method, use its text content
                        text_content = file_obj.data.text if hasattr(file_obj.data, 'text') else str(file_data)
                        results.append(Data(
                            text=text_content,
                            data={
                                "file_path": getattr(file_obj, 'path', ''),
                                "export_format": "Standard"
                            }
                        ))
            
            # Return DataFrame like Export Docling Document
            return DataFrame(results)
            
        except Exception as e:
            self.log(f"Error in advanced processing: {e}")
            # Fallback to standard processing on error
            return self.load_files()

    def _process_with_docling_and_export(self, file_path: str) -> Data:
        """Process a single file with Docling and export to the specified format."""
        # Import docling components only when needed
        docling_imports = self._try_import_docling()
        
        if docling_imports is None:
            raise ImportError("Docling not available for advanced processing")

        ConversionStatus = docling_imports['ConversionStatus']
        InputFormat = docling_imports['InputFormat']
        DocumentConverter = docling_imports['DocumentConverter']
        ImageRefMode = docling_imports['ImageRefMode']

        try:
            # Create converter based on strategy and pipeline setting
            if docling_imports['strategy'] == 'latest' and self.pipeline == "standard":
                converter = self._create_advanced_converter(docling_imports)
            else:
                # Use basic converter for compatibility
                converter = DocumentConverter()
                self.log("Using basic DocumentConverter for Docling processing")

            # Process single file
            result = converter.convert(file_path)
            
            # Check if conversion was successful
            success = False
            if hasattr(result, 'status'):
                if hasattr(ConversionStatus, 'SUCCESS'):
                    success = result.status == ConversionStatus.SUCCESS
                else:
                    success = str(result.status).lower() == 'success'
            elif hasattr(result, 'document'):
                # If no status but has document, assume success
                success = result.document is not None
            
            if success:
                # Export the document to the specified format
                exported_content = self._export_document(result.document, ImageRefMode)
                
                return Data(
                    text=exported_content,
                    data={
                        "doc": result.document,
                        "exported_content": exported_content,
                        "export_format": self.EXPORT_FORMAT,
                        "file_path": file_path
                    }
                )
            else:
                return Data(data={
                    "error": "Docling conversion failed", 
                    "file_path": file_path
                })
                
        except Exception as e:
            return Data(data={
                "error": f"Docling processing error: {str(e)}", 
                "file_path": file_path
            })

    def _export_document(self, document, ImageRefMode):
        """Export document to Markdown format with placeholder images."""
        try:
            image_mode = ImageRefMode(self.IMAGE_MODE) if hasattr(ImageRefMode, self.IMAGE_MODE) else self.IMAGE_MODE
            
            # Always export to Markdown since it's fixed
            return document.export_to_markdown(
                image_mode=image_mode,
                image_placeholder=self.md_image_placeholder,
                page_break_placeholder=self.md_page_break_placeholder,
            )
                
        except Exception as e:
            self.log(f"Markdown export failed: {e}, using basic text export")
            # Fallback to basic text export
            try:
                return document.export_to_text()
            except:
                return str(document) 