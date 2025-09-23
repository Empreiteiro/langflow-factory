from pathlib import Path
from typing import Any, Dict, Union

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema import Data


class S3BucketUploaderComponent(Component):
    """S3BucketUploaderComponent is a component responsible for uploading files to an S3 bucket.

    This component processes various types of content (text, messages, dataframes) and uploads them
    to a specified S3 bucket. It creates temporary files when needed and handles binary content
    including PDF conversion.

    Attributes:
        display_name (str): The display name of the component.
        description (str): A brief description of the components functionality.
        icon (str): The icon representing the component.
        name (str): The internal name of the component.
        inputs (list): A list of input configurations required by the component.
        outputs (list): A list of output configurations provided by the component.

    Methods:
        upload_files() -> Data:
            Main method that processes content inputs and uploads them to S3.
        process_files_by_name() -> Data:
            Internal method that handles the actual file upload process.
        _s3_client() -> Any:
            Creates and returns an S3 client using the provided AWS credentials.

    Note: This component requires the boto3 library to be installed.
    """

    display_name = "S3 Bucket Uploader"
    description = "Uploads files to S3 bucket."
    icon = "Amazon"
    name = "s3bucketuploader"

    inputs = [
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            required=True,
            password=True,
            info="AWS Access key ID.",
            advanced=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Key",
            required=True,
            password=True,
            info="AWS Secret Key.",
            advanced=True,
        ),
        StrInput(
            name="bucket_name",
            display_name="Bucket Name",
            required=True,
            info="Enter the name of the bucket.",
            advanced=True,
        ),
        HandleInput(
            name="content_input",
            display_name="File Content",
            info="Content to upload to S3. Accepts text, messages, or dataframes.",
            input_types=["Text", "Message", "DataFrame", "Data"],
            is_list=True,
            required=True,
        ),
        StrInput(
            name="aws_region",
            display_name="AWS Region",
            info="AWS region (e.g., us-east-1, eu-west-1). If not specified, uses default region.",
            advanced=True,
        ),
        StrInput(
            name="s3_prefix",
            display_name="S3 Prefix",
            info="Prefix for all files.",
            advanced=True,
        ),
        MessageTextInput(
            name="filename",
            display_name="File Name",
            info="Name for the uploaded file (without extension). Variables: {timestamp} (YYYYMMDD_HHMMSS), {date} (YYYYMMDD), {time} (HHMMSS), {index} (item number), {format} (file extension). Example: 'report_{date}_{index}' → 'report_20241212_1.txt'. Leave empty for auto-generated names.",
        ),
        MessageTextInput(
            name="file_path",
            display_name="File Path",
            info="Custom path/directory for the file within the S3 bucket. Variables: {timestamp}, {date}, {time}, {index}, {format}. Example: 'reports/{date}/data_{index}' → 'reports/20241212/data_1.txt'. Leave empty to use default 'langflow' directory.",
            advanced=True,
        ),
        DropdownInput(
            name="file_format",
            display_name="File Format",
            options=[
                "txt", "json", "csv", "xml", "html", "md", "yaml", "log", 
                "tsv", "jsonl", "parquet", "xlsx", "zip"
            ],
            value="txt",
            info="File format for the uploaded content. Affects file extension and content processing.",
        ),
    ]

    outputs = [
        Output(display_name="Upload Results", name="data", method="upload_files"),
    ]

    def upload_files(self) -> Data:
        """Upload files to S3 bucket.

        This method processes content inputs and uploads them to the specified S3 bucket.
        It creates temporary files when needed and handles various content types including
        text, messages, and dataframes.

        Returns:
            Data: Results of the upload operation including success/error information
        """
        try:
            # Validate inputs
            if not self.bucket_name:
                error_msg = "Bucket name is required"
                self.log(error_msg)
                return Data(data={"error": error_msg, "success": False})
            
            if not self.content_input:
                error_msg = "No content input provided"
                self.log(error_msg)
                return Data(data={"error": error_msg, "success": False})
            
            return self.process_files_by_name()
            
        except Exception as e:
            error_msg = f"Unexpected error in upload_files: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "success": False})


    def process_files_by_name(self) -> Data:
        """Processes and uploads files to an S3 bucket based on their names.

        Iterates through the list of data inputs, retrieves the file path from each data item,
        and uploads the file to the specified S3 bucket. If file_path is missing, creates
        a temporary file from the text content and uploads it.

        Returns:
            Data: Results of the upload operation including success/error information
        """
        uploaded_files = []
        failed_files = []
        temp_files_to_cleanup = []
        
        try:
            s3_client = self._s3_client()
            
            for i, content_item in enumerate(self.content_input):
                try:
                    # Extract content using robust method
                    content_info = self._extract_content_from_input(content_item, i+1)
                    file_path = content_info['file_path']
                    text_content = content_info['text']
                    temp_file_created = False
                    
                    self.log(f"Item {i+1}: Content extracted from {content_info['source']}")
                    
                    # Handle missing file_path by creating temporary file
                    if not file_path:
                        if not text_content:
                            error_msg = f"Item {i+1}: No content found (source: {content_info['source']})"
                            self.log(error_msg)
                            
                            failed_files.append({"item": i+1, "error": error_msg, "source": content_info['source']})
                            continue
                        
                        # Generate full file path with correct extension
                        file_format = getattr(self, 'file_format', 'txt')
                        generated_path = self._generate_file_path(i+1, file_format)
                        filename = Path(generated_path).name  # Extract just the filename for temp file
                        self.log(f"Item {i+1}: Generated file path: {generated_path}")
                        
                        # Create temporary file
                        import tempfile
                        import os
                        
                        temp_dir = tempfile.gettempdir()
                        temp_file_path = os.path.join(temp_dir, filename)
                        # Use the generated path for S3 key, but temp file path for local operations
                        file_path = generated_path
                        
                        try:
                            # Handle binary vs text content for temporary files
                            is_binary = content_info.get('is_binary', False) or self._is_binary_format(filename)
                            file_format = getattr(self, 'file_format', 'txt')
                            
                            
                            if is_binary:
                                # For binary content, write as-is without processing
                                if isinstance(text_content, str):
                                    # Try to decode if it's base64 or use latin-1
                                    try:
                                        import base64
                                        binary_content = base64.b64decode(text_content)
                                        self.log(f"Item {i+1}: Decoded base64 binary content for temp file")
                                    except Exception:
                                        binary_content = text_content.encode('latin-1')
                                        self.log(f"Item {i+1}: Using latin-1 encoding for binary temp file")
                                else:
                                    binary_content = text_content
                                
                                with open(temp_file_path, 'wb') as f:
                                    f.write(binary_content)
                                self.log(f"Item {i+1}: Created binary temp file ({len(binary_content)} bytes)")
                            else:
                                # Process text content and write (skip processing for binary formats)
                                processed_content = self._process_content_by_format(text_content, content_info.get('content_type', 'text'), is_binary)
                                
                                # Write based on content type
                                if isinstance(processed_content, bytes):
                                    with open(temp_file_path, 'wb') as f:
                                        f.write(processed_content)
                                else:
                                    with open(temp_file_path, 'w', encoding='utf-8') as f:
                                        f.write(str(processed_content))
                                self.log(f"Item {i+1}: Created text temp file")
                            
                            temp_file_created = True
                            temp_files_to_cleanup.append(temp_file_path)
                            self.log(f"Item {i+1}: Created temporary file {file_path} from {content_info.get('content_type', 'text')} content")
                        except Exception as e:
                            error_msg = f"Item {i+1}: Failed to create temporary file: {str(e)}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "error": error_msg})
                            continue
                    
                    # Check if file exists (only for non-temporary files)
                    local_file_path = temp_file_path if temp_file_created else file_path
                    file_obj = Path(local_file_path)
                    if not temp_file_created:
                        if not file_obj.exists():
                            error_msg = f"File does not exist: {local_file_path}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "file_path": file_path, "error": error_msg})
                            continue
                        
                        if not file_obj.is_file():
                            error_msg = f"Path is not a file: {local_file_path}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "file_path": file_path, "error": error_msg})
                            continue

                    normalized_path = self._normalize_path(file_path)
                    
                    self.log(f"Uploading file: {file_path} to s3://{self.bucket_name}/{normalized_path}")
                    
                    # For binary files, add ContentType to upload
                    extra_args = {}
                    if self._is_binary_format(file_path):
                        extra_args['ContentType'] = self._get_content_type_for_format(file_path)
                        self.log(f"Item {i+1}: Uploading as binary file with ContentType: {extra_args['ContentType']}")
                    
                    # Upload to S3 (use local file path for reading, S3 key for destination)
                    if extra_args:
                        s3_client.upload_file(
                            Filename=local_file_path, 
                            Bucket=self.bucket_name, 
                            Key=normalized_path,
                            ExtraArgs=extra_args
                        )
                    else:
                        s3_client.upload_file(
                            Filename=local_file_path, 
                            Bucket=self.bucket_name, 
                            Key=normalized_path
                        )
                    
                    success_msg = f"Successfully uploaded {file_path} to s3://{self.bucket_name}/{normalized_path}"
                    self.log(success_msg)
                    uploaded_files.append({
                        "file_path": file_path if not temp_file_created else f"temp:{filename}",
                        "s3_key": normalized_path,
                        "bucket": self.bucket_name,
                        "size_bytes": file_obj.stat().st_size,
                        "temporary_file": temp_file_created
                    })
                    
                except Exception as e:
                    error_msg = f"Error uploading file {file_path if 'file_path' in locals() else 'unknown'}: {str(e)}"
                    self.log(error_msg)
                    failed_files.append({
                        "item": i+1, 
                        "file_path": file_path if 'file_path' in locals() else None,
                        "error": str(e)
                    })
            
            # Prepare result
            result = {
                "success": len(failed_files) == 0,
                "total_files": len(self.content_input),
                "uploaded_files": len(uploaded_files),
                "failed_files": len(failed_files),
                "uploads": uploaded_files
            }
            
            if failed_files:
                result["errors"] = failed_files
                
            summary_msg = f"Upload completed: {len(uploaded_files)} successful, {len(failed_files)} failed"
            self.log(summary_msg)
            
            return Data(data=result)
            
        except Exception as e:
            error_msg = f"Error in process_files_by_name: {str(e)}"
            self.log(error_msg)
            return Data(data={
                "error": error_msg,
                "success": False,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files
            })
        finally:
            # Clean up temporary files
            for temp_file in temp_files_to_cleanup:
                try:
                    import os
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.log(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.log(f"Warning: Failed to clean up temporary file {temp_file}: {str(e)}")

    def _s3_client(self) -> Any:
        """Creates and returns an S3 client using the provided AWS access key ID and secret access key.

        Returns:
            Any: A boto3 S3 client instance.
            
        Raises:
            ImportError: If boto3 is not installed
            Exception: If there are issues with AWS credentials or client creation
        """
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
        except ImportError as e:
            msg = "boto3 is not installed. Please install it using `uv pip install boto3`."
            raise ImportError(msg) from e

        try:
            # Prepare client configuration
            client_config = {
                "aws_access_key_id": self.aws_access_key_id,
                "aws_secret_access_key": self.aws_secret_access_key,
            }
            
            # Add region if specified
            if hasattr(self, 'aws_region') and self.aws_region:
                client_config["region_name"] = self.aws_region
            
            client = boto3.client("s3", **client_config)
            
            # Test credentials by listing buckets (this will raise an exception if credentials are invalid)
            try:
                client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise Exception(f"Bucket '{self.bucket_name}' does not exist or you don't have access to it")
                elif error_code == '403':
                    raise Exception(f"Access denied to bucket '{self.bucket_name}'. Check your credentials and permissions")
                else:
                    raise Exception(f"Error accessing bucket '{self.bucket_name}': {e.response['Error']['Message']}")
            
            return client
            
        except NoCredentialsError as e:
            raise Exception("AWS credentials not found. Please provide valid AWS Access Key ID and Secret Access Key") from e
        except ClientError as e:
            raise Exception(f"AWS client error: {e.response['Error']['Message']}") from e
        except Exception as e:
            if "Bucket" in str(e):
                raise  # Re-raise bucket-specific errors
            raise Exception(f"Error creating S3 client: {str(e)}") from e

    def _generate_file_path(self, item_index: int, file_format: str) -> str:
        """Generate full file path based on user configuration or defaults.
        
        Args:
            item_index: Index of the current item being processed
            file_format: File format extension
            
        Returns:
            Complete file path with filename and extension
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            date = datetime.now().strftime("%Y%m%d")
            time = datetime.now().strftime("%H%M%S")
            
            # Template variables
            template_vars = {
                'timestamp': timestamp,
                'index': item_index,
                'format': file_format,
                'date': date,
                'time': time
            }
            
            # Get user-defined filename and path
            user_filename = getattr(self, 'filename', '').strip()
            user_file_path = getattr(self, 'file_path', '').strip()
            
            # Generate filename
            if user_filename:
                processed_filename = user_filename.format(**template_vars)
                # Ensure it doesn't already have extension
                base_name = Path(processed_filename).stem
                filename = f"{base_name}.{file_format}"
            else:
                # Generate default timestamp-based filename
                filename = f"data_{timestamp}_{item_index}.{file_format}"
            
            # Generate full path
            if user_file_path:
                processed_path = user_file_path.format(**template_vars)
                # Combine path and filename
                full_path = f"{processed_path.rstrip('/')}/{filename}"
            else:
                # Use default "langflow" path when no custom path is specified
                full_path = f"langflow/{filename}"
            
            return full_path
                
        except Exception as e:
            # Fallback to simple default if template processing fails
            self.log(f"Error processing file path template: {str(e)}, using default")
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"langflow/data_{timestamp}_{item_index}.{file_format}"

    def _normalize_path(self, file_path) -> str:
        """Process the file path based on the s3_prefix setting.

        Args:
            file_path (str): The original file path.

        Returns:
            str: The processed file path for S3 key.
        """
        prefix = getattr(self, 's3_prefix', '') or ''
        processed_path: str = file_path

        # Concatenate the s3_prefix if it exists
        if prefix:
            processed_path = str(Path(prefix) / processed_path)
        
        # Ensure we don't start with a slash (S3 keys shouldn't start with /)
        processed_path = processed_path.lstrip('/')

        return processed_path
    
    def _extract_content_from_data(self, data_item: Data, item_index: int) -> Dict[str, Any]:
        """Extract file_path and text content from various Data object formats.
        
        Args:
            data_item: The Data object to extract content from
            item_index: Index of the item for logging purposes
            
        Returns:
            Dict containing 'file_path', 'text', and 'source' information
        """
        result = {
            'file_path': None,
            'text': None,
            'source': 'unknown',
            'is_binary': False,
            'content_type': 'text'
        }
        
        try:
            # Try to access data_item.data first (most common case)
            if hasattr(data_item, 'data') and data_item.data:
                data_dict = data_item.data
                
                # Direct access to file_path and text
                result['file_path'] = data_dict.get('file_path')
                result['text'] = data_dict.get('text')
                
                if result['file_path'] or result['text']:
                    result['source'] = 'data.data'
                    # Check if content is binary
                    if result['file_path'] and self._is_binary_format(result['file_path']):
                        result['is_binary'] = True
                        result['content_type'] = 'binary'
                    elif result['text'] and self._is_binary_content(result['text']):
                        result['is_binary'] = True
                        result['content_type'] = 'binary'
                    return result
                
                # Try other common keys for text content
                for text_key in ['content', 'body', 'message', 'payload', 'value', 'result']:
                    if text_key in data_dict and data_dict[text_key]:
                        result['text'] = str(data_dict[text_key])
                        result['source'] = f'data.data.{text_key}'
                        break
                
                # If data_dict itself is a string
                if isinstance(data_dict, str) and data_dict.strip():
                    result['text'] = data_dict
                    result['source'] = 'data.data (string)'
                    return result
                
                # If data_dict is a list, try to extract from first item
                if isinstance(data_dict, list) and len(data_dict) > 0:
                    first_item = data_dict[0]
                    if isinstance(first_item, dict):
                        result['file_path'] = first_item.get('file_path')
                        result['text'] = first_item.get('text') or first_item.get('content')
                        if result['file_path'] or result['text']:
                            result['source'] = 'data.data[0]'
                            return result
                    elif isinstance(first_item, str):
                        result['text'] = first_item
                        result['source'] = 'data.data[0] (string)'
                        return result
            
            # Try direct attributes on data_item
            if hasattr(data_item, 'text') and data_item.text:
                result['text'] = data_item.text
                result['source'] = 'data_item.text'
                return result
            
            if hasattr(data_item, 'content') and data_item.content:
                result['text'] = str(data_item.content)
                result['source'] = 'data_item.content'
                return result
            
            # Try to convert the entire data_item to string as last resort
            if hasattr(data_item, '__dict__'):
                data_str = str(data_item)
                if data_str and data_str != 'Data(data={})' and len(data_str) > 20:
                    result['text'] = data_str
                    result['source'] = 'data_item (string conversion)'
                    return result
            
            # If all else fails, try to serialize the data
            try:
                import json
                if hasattr(data_item, 'data') and data_item.data:
                    json_str = json.dumps(data_item.data, indent=2, default=str)
                    if json_str and json_str != '{}' and json_str != 'null':
                        result['text'] = json_str
                        result['source'] = 'data.data (JSON)'
                        return result
            except Exception:
                pass
                
        except Exception as e:
            self.log(f"Error extracting content from item {item_index}: {str(e)}")
        
        return result
    
    def _extract_content_from_input(self, input_item: Any, item_index: int) -> Dict[str, Any]:
        """Extract content from various input types (Text, Message, DataFrame, Data).
        
        Args:
            input_item: The input item to extract content from
            item_index: Index of the item for logging purposes
            
        Returns:
            Dict containing 'file_path', 'text', 'content_type', 'is_binary', and 'source' information
        """
        result = {
            'file_path': None,
            'text': None,
            'content_type': 'text',
            'is_binary': False,
            'source': 'unknown'
        }
        
        try:
            # Handle string/text input
            if isinstance(input_item, str):
                result['text'] = input_item
                result['source'] = 'string'
                result['content_type'] = 'text'
                return result
            
            # Handle Message objects
            if hasattr(input_item, 'text') and input_item.text:
                result['text'] = input_item.text
                result['source'] = 'message.text'
                result['content_type'] = 'text'
                return result
            
            # Handle DataFrame objects
            if hasattr(input_item, 'to_csv') or str(type(input_item)).find('DataFrame') != -1:
                try:
                    # Try to convert DataFrame to CSV
                    if hasattr(input_item, 'to_csv'):
                        result['text'] = input_item.to_csv(index=False)
                        result['content_type'] = 'dataframe'
                        result['source'] = 'dataframe.to_csv'
                        return result
                except Exception as e:
                    self.log(f"Failed to convert DataFrame to CSV: {str(e)}")
            
            # Handle Data objects (fallback to original method)
            if hasattr(input_item, 'data'):
                data_result = self._extract_content_from_data(input_item, item_index)
                # Check if the data contains binary content
                if data_result.get('text'):
                    file_path = data_result.get('file_path', '')
                    if self._is_binary_format(file_path) or self._is_binary_content(data_result.get('text')):
                        data_result['is_binary'] = True
                        data_result['content_type'] = 'binary'
                return data_result
            
            # Last resort: convert to string
            text_str = str(input_item)
            if text_str and len(text_str) > 10:  # Avoid empty or very short strings
                result['text'] = text_str
                result['source'] = 'string_conversion'
                result['content_type'] = 'text'
                return result
                
        except Exception as e:
            self.log(f"Error extracting content from input item {item_index}: {str(e)}")
        
        return result
    
    def _process_content_by_format(self, content: Union[str, bytes], content_type: str, is_binary: bool = False) -> Union[str, bytes]:
        """Process content based on the selected file format.
        
        Args:
            content: The content to process
            content_type: Type of content (text, dataframe, etc.)
            is_binary: Whether the content is binary
            
        Returns:
            Processed content as string or bytes
        """
        file_format = getattr(self, 'file_format', 'txt')
        
        if not content:
            return content
        
        # For binary content or binary formats, return as-is without processing
        if is_binary or file_format in ['zip', 'xlsx', 'parquet', 'jpg', 'png']:
            self.log(f"Skipping text processing for binary format: {file_format}")
            return content
        
        try:
            # Handle DataFrame content
            if content_type == 'dataframe':
                if file_format == 'json':
                    # Convert CSV back to DataFrame and then to JSON
                    try:
                        import pandas as pd
                        from io import StringIO
                        df = pd.read_csv(StringIO(content))
                        return df.to_json(orient='records', indent=2)
                    except Exception:
                        return content  # Fallback to CSV
                elif file_format in ['csv', 'tsv']:
                    if file_format == 'tsv':
                        # Convert CSV to TSV
                        lines = content.split('\n')
                        tsv_lines = [line.replace(',', '\t') for line in lines]
                        return '\n'.join(tsv_lines)
                    return content  # Already CSV
                else:
                    return content  # Keep as CSV for other formats
            
            # Handle JSON formatting
            if file_format == 'json':
                try:
                    import json
                    # Try to parse and reformat if it's already JSON
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    # If not JSON, wrap in a JSON structure
                    return json.dumps({"content": content}, indent=2, ensure_ascii=False)
            
            # Handle XML formatting
            elif file_format == 'xml':
                if not content.strip().startswith('<'):
                    return f"<?xml version='1.0' encoding='UTF-8'?>\n<data>\n  <content>{content}</content>\n</data>"
                return content
            
            # Handle HTML formatting
            elif file_format == 'html':
                if not content.strip().startswith('<'):
                    return f"<!DOCTYPE html>\n<html>\n<head><title>Data</title></head>\n<body>\n<pre>{content}</pre>\n</body>\n</html>"
                return content
            
            # Handle YAML formatting
            elif file_format == 'yaml':
                try:
                    import yaml
                    # Try to parse as JSON first, then convert to YAML
                    try:
                        import json
                        data = json.loads(content)
                        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
                    except json.JSONDecodeError:
                        # Wrap text content in YAML structure
                        return yaml.dump({"content": content}, default_flow_style=False, allow_unicode=True)
                except ImportError:
                    # Fallback if PyYAML not available
                    return f"content: |\n  {content.replace(chr(10), chr(10) + '  ')}"
            
            # For other formats, return as-is
            return content
            
        except Exception as e:
            self.log(f"Error processing content for format {file_format}: {str(e)}")
            return content  # Return original content on error
    
    def _get_content_type_for_format(self, file_path: str = None) -> str:
        """Get the appropriate Content-Type header for the selected file format.
        
        Args:
            file_path: Optional file path to help determine content type
            
        Returns:
            MIME type string
        """
        file_format = getattr(self, 'file_format', 'txt')
        
        content_types = {
            'txt': 'text/plain',
            'json': 'application/json',
            'csv': 'text/csv',
            'xml': 'application/xml',
            'html': 'text/html',
            'md': 'text/markdown',
            'yaml': 'application/x-yaml',
            'log': 'text/plain',
            'tsv': 'text/tab-separated-values',
            'jsonl': 'application/jsonlines',
            'parquet': 'application/octet-stream',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'zip': 'application/zip',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp'
        }
        
        # If file_path is provided and format is not explicitly set, try to infer from extension
        if file_path and file_format == 'txt':
            ext = Path(file_path).suffix.lower().lstrip('.')
            if ext in content_types:
                return content_types[ext]
        
        return content_types.get(file_format, 'text/plain')
    
    def _is_binary_format(self, file_path: str) -> bool:
        """Check if the file format is binary based on file extension.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if binary format, False otherwise
        """
        if not file_path:
            return False
            
        binary_extensions = {
            '.zip', '.xlsx', '.docx', '.pptx', '.jpg', '.jpeg', '.png', 
            '.gif', '.bmp', '.ico', '.mp3', '.mp4', '.avi', '.mov', '.exe', 
            '.dll', '.so', '.bin', '.dat', '.db', '.sqlite', '.parquet'
        }
        
        file_format = getattr(self, 'file_format', 'txt')
        if file_format in ['zip', 'xlsx', 'parquet']:
            return True
            
        extension = Path(file_path).suffix.lower()
        return extension in binary_extensions
    
    def _is_binary_content(self, content: Any) -> bool:
        """Check if content is binary data.
        
        Args:
            content: Content to check
            
        Returns:
            True if binary content, False otherwise
        """
        if isinstance(content, bytes):
            return True
            
        if isinstance(content, str):
            # Check for binary indicators in string content
            try:
                # Try to encode/decode - if it fails, likely binary
                content.encode('utf-8')
                # Check for null bytes or other binary indicators
                if '\x00' in content or len(content) > 100 and content.count('\\x') > len(content) * 0.1:
                    return True
            except UnicodeEncodeError:
                return True
                
        return False
    
    
    def _read_binary_file(self, file_path: str) -> bytes:
        """Read a file as binary data.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Binary content of the file
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.log(f"Error reading binary file {file_path}: {str(e)}")
            raise
