import json
from typing import Any

from langchain_text_splitters import RecursiveJsonSplitter

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, IntInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class RecursiveJsonSplitterComponent(Component):
    display_name = "Recursive JSON Splitter"
    description = "Split JSON documents recursively into smaller chunks using LangChain's RecursiveJsonSplitter. Maintains object integrity - never splits a single object/item in half."
    icon = "scissors"
    name = "RecursiveJsonSplitter"

    inputs = [
        DataInput(
            name="json_data",
            display_name="JSON Data",
            info="The JSON data to split. Can be a Data object containing JSON or a JSON string.",
            required=True,
        ),
        IntInput(
            name="chunk_size",
            display_name="Chunk Size",
            value=1000,
            info="The maximum size for each chunk in characters. Objects are grouped together to stay within this size. Minimum: 100.",
        ),
    ]

    outputs = [
        Output(
            display_name="Chunks",
            name="dataframe",
            method="split_json",
            info="DataFrame with JSON chunks, where each row contains a chunk.",
        )
    ]

    def split_json(self) -> DataFrame:
        """Split JSON data recursively into smaller chunks, ensuring each chunk is valid JSON."""
        # Validate chunk_size
        if self.chunk_size < 100:
            msg = f"chunk_size must be at least 100, got {self.chunk_size}"
            raise ValueError(msg)

        # Extract JSON from input
        json_content = self._extract_json(self.json_data)

        # RecursiveJsonSplitter expects a dict or list, not a string
        if isinstance(json_content, str):
            try:
                json_content = json.loads(json_content)
            except json.JSONDecodeError as e:
                msg = f"Input is not valid JSON: {e}"
                raise ValueError(msg) from e
        
        if not isinstance(json_content, (dict, list)):
            msg = f"Input must be a JSON object (dict) or array (list), got {type(json_content).__name__}"
            raise ValueError(msg)

        # Validate JSON is not empty
        if isinstance(json_content, dict) and len(json_content) == 0:
            msg = "Input JSON object is empty. Cannot split an empty object."
            raise ValueError(msg)
        if isinstance(json_content, list) and len(json_content) == 0:
            msg = "Input JSON array is empty. Cannot split an empty array."
            raise ValueError(msg)

        # Use LangChain's RecursiveJsonSplitter
        splitter = RecursiveJsonSplitter(
            max_chunk_size=self.chunk_size,
        )
        
        # Use split_json method which returns valid JSON chunks (dicts/lists)
        # Wrap in try/except to handle internal bugs in RecursiveJsonSplitter
        chunks = None
        original_error = None
        
        try:
            chunks = splitter.split_json(json_content)
        except (IndexError, KeyError) as e:
            # Handle known bug in RecursiveJsonSplitter with certain JSON structures
            # This can happen when the splitter encounters empty paths or certain nested structures
            original_error = e
            self.log(f"RecursiveJsonSplitter encountered an internal error: {e}. Attempting to wrap JSON in root object...")
            
            # Try wrapping the JSON in a root object as a workaround
            try:
                if isinstance(json_content, dict):
                    # If it's already a dict, wrap it
                    wrapped_content = {"data": json_content}
                elif isinstance(json_content, list):
                    # If it's a list, wrap it
                    wrapped_content = {"items": json_content}
                else:
                    wrapped_content = {"data": json_content}
                
                # Try again with wrapped content
                chunks = splitter.split_json(wrapped_content)
                self.log("Successfully split JSON after wrapping in root object.")
            except (IndexError, KeyError) as retry_error:
                # If wrapping also fails, raise the original error with helpful message
                error_msg = (
                    f"RecursiveJsonSplitter encountered an internal error: {original_error}. "
                    "Attempted automatic workaround (wrapping in root object) but it also failed. "
                    "This is a known issue with certain JSON structures. "
                    "Possible solutions:\n"
                    "1. Manually wrap your JSON in a root object (e.g., {{\"data\": <your_json>}})\n"
                    "2. Increase the chunk_size parameter\n"
                    "3. Simplify the JSON structure if possible"
                )
                self.log(error_msg)
                raise ValueError(error_msg) from original_error
            except Exception as retry_error:
                # If wrapping causes a different error, raise with context
                error_msg = (
                    f"RecursiveJsonSplitter failed with original error: {original_error}. "
                    f"Attempted workaround but encountered: {type(retry_error).__name__}: {retry_error}. "
                    "Please check your JSON structure and chunk_size parameter."
                )
                self.log(error_msg)
                raise ValueError(error_msg) from retry_error
        except Exception as e:
            # Catch any other unexpected errors from the splitter
            error_msg = (
                f"Error splitting JSON with RecursiveJsonSplitter: {type(e).__name__}: {e}. "
                "Please check your JSON structure and chunk_size parameter."
            )
            self.log(error_msg)
            raise ValueError(error_msg) from e
        
        # If chunks is still None, something went wrong
        if chunks is None:
            error_msg = "Failed to split JSON: no chunks were generated."
            self.log(error_msg)
            raise ValueError(error_msg)

        # Convert chunks to Data objects for DataFrame
        result = []
        for i, chunk in enumerate(chunks):
            try:
                is_valid_json = False
                chunk_metadata = {}
                
                # Handle different chunk formats
                if isinstance(chunk, (dict, list)):
                    # RecursiveJsonSplitter returns dict/list chunks
                    # Validate it's valid JSON before converting
                    try:
                        # Test serialization
                        chunk_text = json.dumps(chunk, indent=2, ensure_ascii=False)
                        # Validate it can be parsed back
                        json.loads(chunk_text)
                        chunk_data = chunk
                        is_valid_json = True
                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                        # If not valid JSON, wrap it
                        self.log(f"Chunk {i} is not valid JSON, wrapping: {e}")
                        chunk_data = {"data": chunk}
                        chunk_text = json.dumps(chunk_data, indent=2, ensure_ascii=False)
                        is_valid_json = True
                elif isinstance(chunk, str):
                    # String chunk - try to parse as JSON
                    chunk_text = chunk
                    try:
                        chunk_data = json.loads(chunk)
                        is_valid_json = True
                    except json.JSONDecodeError:
                        # Not valid JSON, store as text
                        chunk_data = chunk
                        is_valid_json = False
                elif hasattr(chunk, 'page_content'):
                    # LangChain Document object
                    chunk_text = chunk.page_content
                    chunk_metadata = getattr(chunk, 'metadata', {})
                    try:
                        chunk_data = json.loads(chunk_text)
                        is_valid_json = True
                    except json.JSONDecodeError:
                        chunk_data = chunk_text
                        is_valid_json = False
                elif hasattr(chunk, 'text'):
                    # Object with text attribute
                    chunk_text = chunk.text
                    chunk_metadata = getattr(chunk, 'metadata', {}) if hasattr(chunk, 'metadata') else {}
                    try:
                        chunk_data = json.loads(chunk_text)
                        is_valid_json = True
                    except json.JSONDecodeError:
                        chunk_data = chunk_text
                        is_valid_json = False
                else:
                    # Other types - convert to JSON
                    try:
                        chunk_text = json.dumps(chunk, indent=2, ensure_ascii=False)
                        chunk_data = json.loads(chunk_text)
                        is_valid_json = True
                    except (TypeError, ValueError, json.JSONDecodeError):
                        chunk_text = str(chunk)
                        chunk_data = {"data": str(chunk)}
                        is_valid_json = False
                
                # Create Data object with text and metadata
                result.append(Data(
                    text=chunk_text,
                    data={
                        "chunk_index": i,
                        "content": chunk_data,
                        "is_valid_json": is_valid_json,
                        **chunk_metadata,  # Include any metadata from the chunk
                    }
                ))
            except Exception as e:
                self.log(f"Error processing chunk {i}: {e}")
                result.append(Data(
                    text=json.dumps(chunk) if isinstance(chunk, (dict, list)) else str(chunk),
                    data={
                        "chunk_index": i,
                        "content": str(chunk),
                        "is_valid_json": False,
                    }
                ))

        # Final validation: ensure all chunks have valid JSON in text field
        validated_result = []
        for i, data_obj in enumerate(result):
            try:
                # Validate the text field is valid JSON
                text_content = data_obj.text if hasattr(data_obj, 'text') else str(data_obj)
                if isinstance(text_content, str):
                    try:
                        # Try to parse as JSON
                        json.loads(text_content)
                        validated_result.append(data_obj)
                    except json.JSONDecodeError:
                        # If not valid JSON, try to fix it
                        self.log(f"Chunk {i} text is not valid JSON, attempting to fix")
                        # Get the content from data field
                        content = data_obj.data.get("content", text_content) if hasattr(data_obj, 'data') else text_content
                        # Ensure content is valid JSON
                        if isinstance(content, (dict, list)):
                            fixed_text = json.dumps(content, indent=2, ensure_ascii=False)
                            validated_result.append(Data(
                                text=fixed_text,
                                data=data_obj.data if hasattr(data_obj, 'data') else {"content": content}
                            ))
                        else:
                            # Wrap in a dict to make it valid JSON
                            fixed_text = json.dumps({"data": content}, indent=2, ensure_ascii=False)
                            validated_result.append(Data(
                                text=fixed_text,
                                data=data_obj.data if hasattr(data_obj, 'data') else {"content": content}
                            ))
                else:
                    validated_result.append(data_obj)
            except Exception as e:
                self.log(f"Error validating chunk {i}: {e}")
                validated_result.append(data_obj)
        
        # Log info instead of using self.status (which interferes with DataFrame display)
        self.log(f"Split JSON into {len(validated_result)} valid chunks")
        return DataFrame(validated_result)

    def _extract_json(self, data: Any) -> Any:
        """Extract JSON content from various input types."""
        if isinstance(data, Data):
            # If it's a Data object, get the data field
            content = data.data
            # If data is a dict with a 'data' key, try to get that
            if isinstance(content, dict) and "data" in content:
                content = content["data"]
            # If content is a string, try to parse as JSON
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
            return content
        elif isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        elif isinstance(data, dict):
            return data
        else:
            # Try to convert to dict
            try:
                return json.loads(str(data))
            except (json.JSONDecodeError, ValueError):
                return data

