from copy import deepcopy
from typing import Any

from langflow.base.data.base_file import BaseFileComponent
from langflow.base.data.utils import TEXT_FILE_TYPES, parallel_load_data, parse_text_file_to_data
from langflow.io import BoolInput, FileInput, IntInput, Output, StrInput, DataInput, DropdownInput
from langflow.inputs import SortableListInput
from langflow.schema.data import Data


class DocumentIntelligenceComponent(BaseFileComponent):
    """Document Intelligence component that performs various AI-powered actions on documents.

    This component supports data extraction, summarization, translation, document classification,
    chunk classification, and text quantification using LLM models.
    """

    display_name = "Document Intelligence"
    description = "Performs AI-powered document analysis and processing with configurable actions."
    icon = "file-text"
    name = "DocumentIntelligence"

    VALID_EXTENSIONS = TEXT_FILE_TYPES

    _base_inputs = deepcopy(BaseFileComponent._base_inputs)

    for input_item in _base_inputs:
        if isinstance(input_item, FileInput) and input_item.name == "path":
            input_item.real_time_refresh = True
            break

    inputs = [
        DataInput(
            name="llm",
            display_name="Language Model",
            info="Language model to use for document intelligence tasks.",
            input_types=["LanguageModel"],
        ),        
        *_base_inputs,
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="Choose the document intelligence action to perform.",
            options=[
                {"name": "Data Extraction", "icon": "search"},
                {"name": "Summarization", "icon": "file-text"},
                {"name": "Translation", "icon": "globe"},
                {"name": "Document Classification", "icon": "folder"},
                {"name": "Chunk Classification", "icon": "grid"},
                {"name": "Text Quantification", "icon": "bar-chart"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        DropdownInput(
            name="target_language",
            display_name="Target Language", 
            show=False,
            info="Select the target language for translation.",
            options=[
                "Portuguese",
                "Spanish", 
                "French",
                "English",
                "German",
                "Italian",
                "Chinese",
                "Japanese",
                "Korean",
                "Russian",
                "Arabic",
                "Hindi",
                "Dutch",
                "Swedish",
                "Norwegian"
            ],
            value="Portuguese"
        ),
        StrInput(
            name="extraction_fields",
            display_name="Extraction Fields",
            show=False,
            info="Comma-separated list of fields to extract (e.g., 'name, email, phone, address')."
        ),
        StrInput(
            name="classification_categories",
            display_name="Classification Categories",
            show=False,
            info="Comma-separated list of categories for classification (e.g., 'invoice, contract, report, letter')."
        ),
        StrInput(
            name="quantification_metrics",
            display_name="Quantification Metrics",
            show=False,
            info="Comma-separated list of metrics to quantify (e.g., 'word_count, sentence_count, paragraph_count, reading_time')."
        ),
        StrInput(
            name="custom_prompt",
            display_name="Custom Prompt",
            show=False,
            info="Custom prompt to override default prompts for the selected action.",
            advanced=True,
        ),
        IntInput(
            name="max_tokens",
            display_name="Max Tokens",
            show=False,
            info="Maximum number of tokens for the LLM response.",
            value=1000,
            advanced=True,
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
        Output(display_name="Processed Content", name="result", method="process_documents"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Data Extraction": ["extraction_fields", "custom_prompt", "max_tokens"],
            "Summarization": ["custom_prompt", "max_tokens"],
            "Translation": ["target_language", "custom_prompt", "max_tokens"],
            "Document Classification": ["classification_categories", "custom_prompt", "max_tokens"],
            "Chunk Classification": ["classification_categories", "custom_prompt", "max_tokens"],
            "Text Quantification": ["quantification_metrics", "custom_prompt", "max_tokens"],
        }

        # Hide all dynamic fields first
        for field_name in ["target_language", "extraction_fields", "classification_categories", 
                          "quantification_metrics", "custom_prompt", "max_tokens"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def process_documents(self) -> Data:
        """Process documents based on the selected action."""
        
        # Validate required inputs
        if not hasattr(self, 'action') or not self.action:
            return Data(data={"error": "Action is required"})
        
        if not hasattr(self, 'llm') or not self.llm:
            return Data(data={"error": "LLM model is required"})

        # Extract action name from the selected action
        action_name = None
        if isinstance(self.action, list) and len(self.action) > 0:
            action_name = self.action[0].get("name")
        elif isinstance(self.action, dict):
            action_name = self.action.get("name")
        
        if not action_name:
            return Data(data={"error": "Invalid action selected"})

        try:
            # Process files directly
            documents = []
            
            # Get file paths
            file_paths = []
            if hasattr(self, 'path') and self.path:
                if isinstance(self.path, list):
                    file_paths = self.path
                else:
                    file_paths = [self.path]
            else:
                return Data(data={"error": "No file path provided"})
            
            if not file_paths:
                return Data(data={"error": "No files found to process"})
            
            # Process each file directly
            for file_path in file_paths:
                try:
                    # Parse the file to get text content
                    data = parse_text_file_to_data(file_path, silent_errors=False)
                    if data and hasattr(data, 'text'):
                        documents.append({
                            "content": data.text,
                            "path": str(file_path)
                        })
                except Exception as e:
                    self.log(f"Error processing file {file_path}: {e}")
                    continue
            
            if not documents:
                return Data(data={"error": "No text content found in the processed files"})
            
            # Process each document with the selected action
            results = []
            for doc in documents:
                result = self.perform_action(action_name, doc["content"], doc["path"])
                results.append({
                    "file_path": doc["path"],
                    "action": action_name,
                    "result": result
                })
            
            return Data(data={
                "action_performed": action_name,
                "files_processed": len(results),
                "results": results
            })
            
        except Exception as e:
            error_msg = f"Error processing documents: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg})

    def perform_action(self, action_name: str, content: str, file_path: str) -> str:
        """Perform the specified action on the document content."""
        
        try:
            # Get custom prompt or use default
            custom_prompt = getattr(self, 'custom_prompt', None)
            max_tokens = getattr(self, 'max_tokens', 1000)
            
            if custom_prompt:
                prompt = f"{custom_prompt}\n\nDocument content:\n{content}"
            else:
                prompt = self.get_default_prompt(action_name, content)
            
            # Generate response using LLM
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                if hasattr(response, 'content'):
                    return response.content
                else:
                    return str(response)
            else:
                return "Error: LLM model does not support invoke method"
                
        except Exception as e:
            return f"Error processing with LLM: {str(e)}"

    def get_default_prompt(self, action_name: str, content: str) -> str:
        """Get default prompt for each action type."""
        
        prompts = {
            "Data Extraction": self.get_extraction_prompt(content),
            "Summarization": self.get_summarization_prompt(content),
            "Translation": self.get_translation_prompt(content),
            "Document Classification": self.get_classification_prompt(content),
            "Chunk Classification": self.get_chunk_classification_prompt(content),
            "Text Quantification": self.get_quantification_prompt(content),
        }
        
        return prompts.get(action_name, f"Analyze the following document:\n\n{content}")

    def get_extraction_prompt(self, content: str) -> str:
        fields = getattr(self, 'extraction_fields', 'name, email, phone, address, date')
        return f"""Extract the following information from the document:
Fields to extract: {fields}

Return the extracted information in a structured format (JSON if possible).

Document content:
{content}"""

    def get_summarization_prompt(self, content: str) -> str:
        return f"""Please provide a comprehensive summary of the following document. 
Include the main points, key information, and important details.

Document content:
{content}"""

    def get_translation_prompt(self, content: str) -> str:
        target_lang = getattr(self, 'target_language', 'Portuguese')
        return f"""Translate the following document to {target_lang}. 
Maintain the original formatting and structure as much as possible.

Document content:
{content}"""

    def get_classification_prompt(self, content: str) -> str:
        categories = getattr(self, 'classification_categories', 'invoice, contract, report, letter, other')
        return f"""Classify this document into one of the following categories: {categories}

Provide the classification result and explain your reasoning.

Document content:
{content}"""

    def get_chunk_classification_prompt(self, content: str) -> str:
        categories = getattr(self, 'classification_categories', 'header, body, footer, table, list, paragraph')
        return f"""Analyze this document and classify each major section/chunk into one of these categories: {categories}

Provide a structured breakdown of the document sections.

Document content:
{content}"""

    def get_quantification_prompt(self, content: str) -> str:
        metrics = getattr(self, 'quantification_metrics', 'word_count, sentence_count, paragraph_count, reading_time')
        return f"""Analyze the following document and provide quantification metrics for: {metrics}

Return the analysis in a structured format with numerical data.

Document content:
{content}"""

    def process_files(self, file_list: list[BaseFileComponent.BaseFile]) -> list[BaseFileComponent.BaseFile]:
        """Processes files either sequentially or in parallel, depending on concurrency settings.

        Args:
            file_list (list[BaseFileComponent.BaseFile]): List of files to process.

        Returns:
            list[BaseFileComponent.BaseFile]: Updated list of files with merged data.
        """

        def process_file(file_path: str, *, silent_errors: bool = False) -> Data | None:
            """Processes a single file and returns its Data object."""
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

        if not file_list:
            msg = "No files to process."
            raise ValueError(msg)

        concurrency = 1 if not self.use_multithreading else max(1, self.concurrency_multithreading)
        file_count = len(file_list)

        parallel_processing_threshold = 2
        if concurrency < parallel_processing_threshold or file_count < parallel_processing_threshold:
            if file_count > 1:
                self.log(f"Processing {file_count} files sequentially.")
            processed_data = [process_file(str(file.path), silent_errors=self.silent_errors) for file in file_list]
        else:
            self.log(f"Starting parallel processing of {file_count} files with concurrency: {concurrency}.")
            file_paths = [str(file.path) for file in file_list]
            processed_data = parallel_load_data(
                file_paths,
                silent_errors=self.silent_errors,
                load_function=process_file,
                max_concurrency=concurrency,
            )

        # Use rollup_basefile_data to merge processed data with BaseFile objects
        return self.rollup_data(file_list, processed_data)
