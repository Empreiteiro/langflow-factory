from pathlib import Path
from typing import Any, Dict, Union

from langflow.custom.custom_component.component import Component
from langflow.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langflow.schema import Data


class S3BucketUploaderComponent(Component):
    """S3BucketUploaderComponent is a component responsible for uploading files to an S3 bucket.

    It provides two strategies for file upload: "By Data" and "By File Name". The component
    requires AWS credentials and bucket details as inputs and processes files accordingly.

    Attributes:
        display_name (str): The display name of the component.
        description (str): A brief description of the components functionality.
        icon (str): The icon representing the component.
        name (str): The internal name of the component.
        inputs (list): A list of input configurations required by the component.
        outputs (list): A list of output configurations provided by the component.

    Methods:
        process_files() -> None:
            Processes files based on the selected strategy. Calls the appropriate method
            based on the strategy attribute.
        process_files_by_data() -> None:
            Processes and uploads files to an S3 bucket based on the data inputs. Iterates
            over the data inputs, logs the file path and text content, and uploads each file
            to the specified S3 bucket if both file path and text content are available.
        process_files_by_name() -> None:
            Processes and uploads files to an S3 bucket based on their names. Iterates through
            the list of data inputs, retrieves the file path from each data item, and uploads
            the file to the specified S3 bucket if the file path is available. Logs the file
            path being uploaded.
        _s3_client() -> Any:
            Creates and returns an S3 client using the provided AWS access key ID and secret
            access key.

        Please note that this component requires the boto3 library to be installed. It is designed
        to work with File and Director components as inputs
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
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Key",
            required=True,
            password=True,
            info="AWS Secret Key.",
        ),
        StrInput(
            name="bucket_name",
            display_name="Bucket Name",
            info="Enter the name of the bucket.",
            advanced=False,
        ),
        DropdownInput(
            name="strategy",
            display_name="Strategy for file upload",
            options=["Store Data", "Store Original File"],
            value="Store Data",
            info=(
                "Choose the strategy to upload the file. Store Data uploads content directly. "
                "Store Original File uploads as a file (creates temporary file if needed). "
                "Both strategies now work with or without file_path."
            ),
        ),
        HandleInput(
            name="content_input",
            display_name="Content Input",
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
        StrInput(
            name="default_filename",
            display_name="Default Filename",
            info="Default filename to use when file_path is not provided (e.g., 'data.txt'). If empty, will generate based on timestamp.",
            advanced=True,
        ),
        DropdownInput(
            name="file_format",
            display_name="File Format",
            options=[
                "txt", "json", "csv", "xml", "html", "md", "yaml", "log", 
                "tsv", "jsonl", "parquet", "xlsx", "pdf", "zip"
            ],
            value="txt",
            info="File format for the uploaded content. Affects file extension and content processing.",
        ),
        BoolInput(
            name="strip_path",
            display_name="Strip Path",
            info="Removes path from file path.",
            required=True,
            advanced=True,
        ),
        BoolInput(
            name="debug_mode",
            display_name="Debug Mode",
            info="Enable detailed logging for troubleshooting data extraction.",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Upload Results", name="data", method="process_files"),
    ]

    def process_files(self) -> Data:
        """Process files based on the selected strategy.

        This method uses a strategy pattern to process files. The strategy is determined
        by the `self.strategy` attribute, which can be either "Store Data" or "Store Original File".
        Depending on the strategy, the corresponding method (`process_files_by_data` or
        `process_files_by_name`) is called. If an invalid strategy is provided, an error
        is returned.

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
            
            # Debug logging if enabled
            if getattr(self, 'debug_mode', False):
                self.log(f"DEBUG: Processing {len(self.content_input)} content inputs")
                self.log(f"DEBUG: Strategy: {self.strategy}")
                self.log(f"DEBUG: Bucket: {self.bucket_name}")
                self.log(f"DEBUG: File format: {getattr(self, 'file_format', 'txt')}")
                for i, item in enumerate(self.content_input):
                    self.log(f"DEBUG: Item {i+1} type: {type(item)}")
                    if hasattr(item, 'data'):
                        self.log(f"DEBUG: Item {i+1} data type: {type(item.data)}")
                        if isinstance(item.data, dict):
                            self.log(f"DEBUG: Item {i+1} data keys: {list(item.data.keys())}")

            strategy_methods = {
                "Store Data": self.process_files_by_data,
                "Store Original File": self.process_files_by_name,
            }
            
            method = strategy_methods.get(self.strategy)
            if not method:
                error_msg = f"Invalid strategy: {self.strategy}"
                self.log(error_msg)
                return Data(data={"error": error_msg, "success": False})
            
            return method()
            
        except Exception as e:
            error_msg = f"Unexpected error in process_files: {str(e)}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "success": False})

    def process_files_by_data(self) -> Data:
        """Processes and uploads files to an S3 bucket based on the data inputs.

        This method iterates over the data inputs, logs the file path and text content,
        and uploads each file to the specified S3 bucket if both file path and text content
        are available.

        Returns:
            Data: Results of the upload operation including success/error information
        """
        uploaded_files = []
        failed_files = []
        
        try:
            s3_client = self._s3_client()
            
            for i, content_item in enumerate(self.content_input):
                try:
                    # Extract content using robust method
                    content_info = self._extract_content_from_input(content_item, i+1)
                    file_path = content_info['file_path']
                    text_content = content_info['text']
                    
                    # Debug logging if enabled
                    if getattr(self, 'debug_mode', False):
                        self.log(f"Item {i+1} DEBUG: content_item type: {type(content_item)}")
                        if hasattr(content_item, 'data'):
                            self.log(f"Item {i+1} DEBUG: content_item.data type: {type(content_item.data)}")
                            self.log(f"Item {i+1} DEBUG: content_item.data keys: {list(content_item.data.keys()) if isinstance(content_item.data, dict) else 'not a dict'}")
                        self.log(f"Item {i+1} DEBUG: content_info: {content_info}")
                    
                    self.log(f"Item {i+1}: Content extracted from {content_info['source']}")

                    # Generate default filename if file_path is missing
                    if not file_path:
                        file_format = getattr(self, 'file_format', 'txt')
                        if hasattr(self, 'default_filename') and self.default_filename:
                            # Ensure the default filename has the correct extension
                            base_name = Path(self.default_filename).stem
                            file_path = f"{base_name}.{file_format}"
                        else:
                            # Generate timestamp-based filename
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_path = f"data_{timestamp}_{i+1}.{file_format}"
                        
                        self.log(f"Item {i+1}: No file_path provided, using default: {file_path}")
                        
                    if not text_content:
                        error_msg = f"Item {i+1}: No text content found (source: {content_info['source']}) for {file_path}"
                        self.log(error_msg)
                        
                        # In debug mode, show what we actually found
                        if getattr(self, 'debug_mode', False):
                            try:
                                import json
                                debug_data = json.dumps(content_item.data if hasattr(content_item, 'data') else str(content_item), indent=2, default=str)[:500]
                                self.log(f"Item {i+1} DEBUG: Raw data (first 500 chars): {debug_data}")
                            except Exception as e:
                                self.log(f"Item {i+1} DEBUG: Could not serialize data: {str(e)}")
                        
                        failed_files.append({"item": i+1, "file_path": file_path, "error": error_msg, "source": content_info['source']})
                        continue

                    normalized_path = self._normalize_path(file_path)
                    
                    # Handle binary vs text content
                    if content_info.get('is_binary', False):
                        # For binary content, don't process - upload as-is
                        if isinstance(text_content, str):
                            # If binary content came as string (base64, etc.), try to decode
                            try:
                                import base64
                                binary_content = base64.b64decode(text_content)
                                self.log(f"Item {i+1}: Decoded base64 binary content")
                            except Exception:
                                # If not base64, treat as binary string
                                binary_content = text_content.encode('latin-1')
                                self.log(f"Item {i+1}: Using latin-1 encoding for binary content")
                        else:
                            binary_content = text_content
                        
                        # Upload binary content directly
                        s3_client.put_object(
                            Bucket=self.bucket_name, 
                            Key=normalized_path, 
                            Body=binary_content,
                            ContentType=self._get_content_type_for_format()
                        )
                        processed_content = binary_content
                    else:
                        # Process text content based on format
                        processed_content = self._process_content_by_format(text_content, content_info.get('content_type', 'text'))
                        
                        # Upload text content
                        s3_client.put_object(
                            Bucket=self.bucket_name, 
                            Key=normalized_path, 
                            Body=processed_content.encode('utf-8') if isinstance(processed_content, str) else processed_content,
                            ContentType=self._get_content_type_for_format()
                        )
                    
                    success_msg = f"Successfully uploaded data for {file_path} to s3://{self.bucket_name}/{normalized_path}"
                    self.log(success_msg)
                    uploaded_files.append({
                        "file_path": file_path,
                        "s3_key": normalized_path,
                        "bucket": self.bucket_name,
                        "size_bytes": len(processed_content.encode('utf-8')) if isinstance(processed_content, str) else len(processed_content),
                        "file_format": getattr(self, 'file_format', 'txt'),
                        "content_type": self._get_content_type_for_format()
                    })
                    
                except Exception as e:
                    error_msg = f"Error uploading item {i+1} ({file_path if 'file_path' in locals() else 'unknown'}): {str(e)}"
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
            error_msg = f"Error in process_files_by_data: {str(e)}"
            self.log(error_msg)
            return Data(data={
                "error": error_msg,
                "success": False,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files
            })

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
                    
                    # Debug logging if enabled
                    if getattr(self, 'debug_mode', False):
                        self.log(f"Item {i+1} DEBUG: content_item type: {type(content_item)}")
                        if hasattr(content_item, 'data'):
                            self.log(f"Item {i+1} DEBUG: content_item.data type: {type(content_item.data)}")
                            self.log(f"Item {i+1} DEBUG: content_item.data keys: {list(content_item.data.keys()) if isinstance(content_item.data, dict) else 'not a dict'}")
                        self.log(f"Item {i+1} DEBUG: content_info: {content_info}")
                    
                    self.log(f"Item {i+1}: Content extracted from {content_info['source']}")
                    
                    # Handle missing file_path by creating temporary file
                    if not file_path:
                        if not text_content:
                            error_msg = f"Item {i+1}: No content found (source: {content_info['source']})"
                            self.log(error_msg)
                            
                            # In debug mode, show what we actually found
                            if getattr(self, 'debug_mode', False):
                                try:
                                    import json
                                    debug_data = json.dumps(content_item.data if hasattr(content_item, 'data') else str(content_item), indent=2, default=str)[:500]
                                    self.log(f"Item {i+1} DEBUG: Raw data (first 500 chars): {debug_data}")
                                except Exception as e:
                                    self.log(f"Item {i+1} DEBUG: Could not serialize data: {str(e)}")
                            
                            failed_files.append({"item": i+1, "error": error_msg, "source": content_info['source']})
                            continue
                        
                        # Generate default filename with correct extension
                        file_format = getattr(self, 'file_format', 'txt')
                        if hasattr(self, 'default_filename') and self.default_filename:
                            base_name = Path(self.default_filename).stem
                            filename = f"{base_name}.{file_format}"
                        else:
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"data_{timestamp}_{i+1}.{file_format}"
                        
                        # Create temporary file
                        import tempfile
                        import os
                        
                        temp_dir = tempfile.gettempdir()
                        file_path = os.path.join(temp_dir, filename)
                        
                        try:
                            # Handle binary vs text content for temporary files
                            if content_info.get('is_binary', False):
                                # For binary content, write as-is without processing
                                if isinstance(text_content, str):
                                    # Try to decode if it's base64 or use latin-1
                                    try:
                                        import base64
                                        binary_content = base64.b64decode(text_content)
                                    except Exception:
                                        binary_content = text_content.encode('latin-1')
                                else:
                                    binary_content = text_content
                                
                                with open(file_path, 'wb') as f:
                                    f.write(binary_content)
                            else:
                                # Process text content and write
                                processed_content = self._process_content_by_format(text_content, content_info.get('content_type', 'text'))
                                
                                # Write based on content type
                                if isinstance(processed_content, bytes):
                                    with open(file_path, 'wb') as f:
                                        f.write(processed_content)
                                else:
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        f.write(str(processed_content))
                            
                            temp_file_created = True
                            temp_files_to_cleanup.append(file_path)
                            self.log(f"Item {i+1}: Created temporary file {file_path} from {content_info.get('content_type', 'text')} content")
                        except Exception as e:
                            error_msg = f"Item {i+1}: Failed to create temporary file: {str(e)}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "error": error_msg})
                            continue
                    
                    # Check if file exists (only for non-temporary files)
                    file_obj = Path(file_path)
                    if not temp_file_created:
                        if not file_obj.exists():
                            error_msg = f"File does not exist: {file_path}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "file_path": file_path, "error": error_msg})
                            continue
                        
                        if not file_obj.is_file():
                            error_msg = f"Path is not a file: {file_path}"
                            self.log(error_msg)
                            failed_files.append({"item": i+1, "file_path": file_path, "error": error_msg})
                            continue

                    normalized_path = self._normalize_path(file_path)
                    
                    self.log(f"Uploading file: {file_path} to s3://{self.bucket_name}/{normalized_path}")
                    
                    # For binary files, add ContentType to upload
                    extra_args = {}
                    if self._is_binary_format(file_path):
                        extra_args['ContentType'] = self._get_content_type_for_format()
                        self.log(f"Item {i+1}: Uploading as binary file with ContentType: {extra_args['ContentType']}")
                    
                    # Upload to S3
                    if extra_args:
                        s3_client.upload_file(
                            Filename=file_path, 
                            Bucket=self.bucket_name, 
                            Key=normalized_path,
                            ExtraArgs=extra_args
                        )
                    else:
                        s3_client.upload_file(
                            Filename=file_path, 
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

    def _normalize_path(self, file_path) -> str:
        """Process the file path based on the s3_prefix and strip_path settings.

        Args:
            file_path (str): The original file path.

        Returns:
            str: The processed file path for S3 key.
        """
        prefix = getattr(self, 's3_prefix', '') or ''
        strip_path = getattr(self, 'strip_path', False)
        processed_path: str = file_path

        if strip_path:
            # Filename only
            processed_path = Path(file_path).name

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
    
    def _process_content_by_format(self, content: str, content_type: str) -> Union[str, bytes]:
        """Process content based on the selected file format.
        
        Args:
            content: The content to process
            content_type: Type of content (text, dataframe, etc.)
            
        Returns:
            Processed content as string or bytes
        """
        file_format = getattr(self, 'file_format', 'txt')
        
        if not content:
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
    
    def _get_content_type_for_format(self) -> str:
        """Get the appropriate Content-Type header for the selected file format.
        
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
            'pdf': 'application/pdf',
            'zip': 'application/zip'
        }
        
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
            '.pdf', '.zip', '.xlsx', '.docx', '.pptx', '.jpg', '.jpeg', '.png', 
            '.gif', '.bmp', '.ico', '.mp3', '.mp4', '.avi', '.mov', '.exe', 
            '.dll', '.so', '.bin', '.dat', '.db', '.sqlite', '.parquet'
        }
        
        file_format = getattr(self, 'file_format', 'txt')
        if file_format in ['pdf', 'zip', 'xlsx', 'parquet']:
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
