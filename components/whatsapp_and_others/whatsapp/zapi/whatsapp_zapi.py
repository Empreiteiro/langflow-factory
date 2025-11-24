import requests
import urllib3
import re
from lfx.custom import Component
from lfx.inputs import MessageTextInput, DropdownInput, SortableListInput, MultilineInput, MessageInput
from lfx.io import SecretStrInput, IntInput
from lfx.template import Output
from lfx.schema import Data
from lfx.schema.dataframe import DataFrame
import pandas as pd

# Disable SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class APIRequestComponent(Component):
    display_name = "Z-API Request"
    description = (
        "This component sends text or audio messages via Z-API, with configurable instance and token."
    )
    icon = "cloud-upload"
    name = "APIRequestComponent"

    inputs = [
        MessageInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger input to connect with flow (not used in processing).",
            required=False,
            advanced=True,
            show=True
        ),
        SecretStrInput(
            name="zapi_instance",
            display_name="Instance",
            info="Z-API instance ID.",
            required=True,
            advanced=True,
            show=True
        ),
        SecretStrInput(
            name="zapi_token",
            display_name="Token",
            info="Z-API authentication token.",
            required=True,
            advanced=True,
            show=True
        ),
        SecretStrInput(
            name="zapi_client_token",
            display_name="Client Token",
            info="Token enviado no header da requisição.",
            required=True,
            advanced=True,
            show=True
        ),
        SortableListInput(
            name="type",
            display_name="Operation Type",
            placeholder="Select Operation Type",
            info="Select the type of operation to perform.",
            options=[
                {"name": "Text", "icon": "text"},
                {"name": "Audio", "icon": "audio-lines"},
                {"name": "Image", "icon": "image"},
                {"name": "Video", "icon": "clapperboard"},
                {"name": "Document", "icon": "file-text"},
                {"name": "Button List", "icon": "list"},
                {"name": "Get Groups", "icon": "users"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        MessageTextInput(
            name="phone",
            display_name="Phone",
            info="Recipient phone number in international format.",
            required=True,
            show=False
        ),
        MessageTextInput(
            name="message",
            display_name="Message",
            info="Text message to be sent (if type is text).",
            show=False
        ),
        IntInput(
            name="delayMessage",
            display_name="Delay Message (seconds)",
            info="Delay before sending next message (1-15 seconds). Default: 1-3 seconds.",
            value=1,
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="delayTyping",
            display_name="Delay Typing (seconds)",
            info="Delay for 'Typing...' status (1-15 seconds). Default: 0 seconds.",
            value=0,
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="editMessageId",
            display_name="Edit Message ID",
            info="Message ID to edit (requires webhook configuration).",
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="audio",
            display_name="Audio URL/Base64",
            info="Audio URL or Base64 to send (if type is audio).",
            show=False
        ),
        MessageTextInput(
            name="image",
            display_name="Image URL/Base64",
            info="Image URL or Base64 to send (if type is image).",
            show=False
        ),
        MessageTextInput(
            name="image_caption",
            display_name="Image Caption",
            info="Caption for the image (optional).",
            show=False
        ),
        MessageTextInput(
            name="video",
            display_name="Video URL",
            info="Video URL to send (if type is video).",
            show=False
        ),
        MessageTextInput(
            name="caption",
            display_name="Video Caption",
            info="Caption for the video (optional).",
            show=False
        ),
        MessageTextInput(
            name="document", 
            display_name="Document URL", 
            dynamic=True, 
            show=False, 
            tool_mode=True
        ),
        MessageTextInput(
            name="fileName", 
            display_name="File Name", 
            dynamic=True, 
            show=False
        ),
        DropdownInput(
            name="extension",
            display_name="Document Extension",
            options=["pdf"],
            value="pdf",
            dynamic=True,
            show=False,
        ),
        MultilineInput(
            name="buttonList",
            display_name="Button List JSON",
            info="Exemplo: {\"buttons\": [{\"id\": \"1\", \"label\": \"Ótimo\"}, {\"id\": \"2\", \"label\": \"Excelente\"}]}",
            value='{"buttons": [{"id": "1", "label": "Ótimo"}, {"id": "2", "label": "Excelente"}]}',
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="page",
            display_name="Page",
            info="Page number for pagination (used for Get Groups operation).",
            value=1,
            dynamic=True,
            show=False,
        ),
        IntInput(
            name="pageSize",
            display_name="Page Size",
            info="Number of groups per page (used for Get Groups operation).",
            value=10,
            dynamic=True,
            show=False,
        ),
    ]

    field_order = ["trigger", "zapi_instance", "zapi_token", "zapi_client_token", "type", "phone", "message", "delayMessage", "delayTyping", "editMessageId", "audio", "image", "image_caption", "video", "caption", "document", "fileName", "extension", "buttonList", "page", "pageSize"]

    outputs = [
        Output(display_name="API Response", name="api_response", method="send_request"),
        Output(display_name="Groups DataFrame", name="groups_dataframe", method="get_groups_dataframe"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "type":
            return build_config

        # Extract message type from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Text": ["phone", "message", "delayMessage", "delayTyping", "editMessageId"],
            "Audio": ["phone", "audio"],
            "Image": ["phone", "image", "image_caption"],
            "Video": ["phone", "video", "caption"],
            "Document": ["phone", "document", "fileName", "extension"],
            "Button List": ["phone", "message", "buttonList"],
            "Get Groups": ["page", "pageSize"],
        }

        # Hide all dynamic fields first
        for field_name in ["phone", "message", "delayMessage", "delayTyping", "editMessageId", "audio", "image", "image_caption", "video", "caption", "document", "fileName", "extension", "buttonList", "page", "pageSize"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected message type
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def safe_json_parse(self, json_str):
        """Safely parse JSON string to object."""
        import json
        if not json_str:
            return {}
        try:
            if isinstance(json_str, str):
                return json.loads(json_str)
            elif isinstance(json_str, dict):
                return json_str
            else:
                return {}
        except Exception as e:
            self.log(f"Error parsing JSON: {str(e)}")
            return {}

    def send_request(self) -> Data:
        # Handle SecretStrInput properly
        instance = self.zapi_instance
        if hasattr(self.zapi_instance, 'get_secret_value'):
            instance = self.zapi_instance.get_secret_value()
        elif isinstance(self.zapi_instance, str):
            instance = self.zapi_instance
            
        token = self.zapi_token
        if hasattr(self.zapi_token, 'get_secret_value'):
            token = self.zapi_token.get_secret_value()
        elif isinstance(self.zapi_token, str):
            token = self.zapi_token
            
        client_token = self.zapi_client_token
        if hasattr(self.zapi_client_token, 'get_secret_value'):
            client_token = self.zapi_client_token.get_secret_value()
        elif isinstance(self.zapi_client_token, str):
            client_token = self.zapi_client_token
        
        # Extract message type from SortableListInput
        message_type = None
        if hasattr(self, 'type') and self.type:
            if isinstance(self.type, list) and len(self.type) > 0:
                message_type = self.type[0].get("name")
            elif isinstance(self.type, dict):
                message_type = self.type.get("name")
            else:
                message_type = self.type
        
        phone = self.phone

        headers = {
            "Content-Type": "application/json",
            "Client-Token": client_token
        }

        if message_type == "Audio":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-audio"
            payload = {
                "phone": phone,
                "audio": self.audio,
                "viewOnce": False,
                "waveform": True
            }
        elif message_type == "Image":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-image"
            payload = {
                "phone": phone,
                "image": self.image,
                "caption": getattr(self, 'image_caption', ''),
                "viewOnce": False
            }
        elif message_type == "Video":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-video"
            payload = {
                "phone": phone,
                "video": self.video,
                "caption": getattr(self, 'caption', ''),
                "viewOnce": False
            }
        elif message_type == "Document":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-document/{self.extension}"
            payload = {
                "phone": phone,
                "document": self.document,
                "fileName": self.fileName
            }
        elif message_type == "Button List":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-button-list"
            payload = {
                "phone": phone,
                "message": self.message,
                "buttonList": self.safe_json_parse(self.buttonList)
            }
        elif message_type == "Get Groups":
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/groups"
            
            # Obter valores dos campos com tratamento adequado
            page = getattr(self, 'page', 1)
            page_size = getattr(self, 'pageSize', 10)
            
            # Log dos valores originais
            self.log(f"Get Groups - Original page: {page}, type: {type(page)}")
            self.log(f"Get Groups - Original pageSize: {page_size}, type: {type(page_size)}")
            
            # Garantir que os valores são inteiros
            try:
                if page is not None and page != "":
                    page = int(page)
                else:
                    page = 1
                    
                if page_size is not None and page_size != "":
                    page_size = int(page_size)
                else:
                    page_size = 10
            except (ValueError, TypeError) as e:
                self.log(f"Get Groups - Error converting to int: {e}")
                page = 1
                page_size = 10
                
            payload = {
                "page": page,
                "pageSize": page_size
            }
            # Log para debug
            self.log(f"Get Groups - URL: {url}")
            self.log(f"Get Groups - Params: {payload}")
            self.log(f"Get Groups - Final Page: {page}, PageSize: {page_size}")
        else:
            url = f"https://api.z-api.io/instances/{instance}/token/{token}/send-text"
            
            # Validate required fields
            if not phone:
                raise ValueError("Phone number is required for sending text message")
            if not self.message:
                raise ValueError("Message text is required for sending text message")
            
            # Clean phone number - remove any non-numeric characters as per Z-API docs
            phone_clean = ''.join(filter(str.isdigit, str(phone)))
            if not phone_clean:
                raise ValueError("Phone number must contain at least one digit")
            
            payload = {
                "phone": phone_clean,
                "message": str(self.message).strip()
            }
            
            # Validate message is not empty after stripping
            if not payload["message"]:
                raise ValueError("Message cannot be empty")
            
            # Add optional fields if provided
            delay_message = getattr(self, 'delayMessage', None)
            if delay_message is not None and delay_message != "":
                try:
                    delay_message = int(delay_message)
                    if 1 <= delay_message <= 15:
                        payload["delayMessage"] = delay_message
                except (ValueError, TypeError):
                    pass
            
            delay_typing = getattr(self, 'delayTyping', None)
            if delay_typing is not None and delay_typing != "":
                try:
                    delay_typing = int(delay_typing)
                    if 1 <= delay_typing <= 15:
                        payload["delayTyping"] = delay_typing
                except (ValueError, TypeError):
                    pass
            
            edit_message_id = getattr(self, 'editMessageId', None)
            if edit_message_id and edit_message_id.strip():
                payload["editMessageId"] = edit_message_id.strip()

        try:
            # Set timeout to avoid hanging requests (30 seconds)
            timeout = 30
            
            # Log request details for debugging
            self.log(f"Request URL: {url}")
            self.log(f"Request payload: {payload}")
            self.log(f"Request headers: {{'Content-Type': 'application/json', 'Client-Token': '***'}}")
            
            if message_type == "Get Groups":
                # Para GET requests, os parâmetros devem ser passados como query parameters
                response = requests.get(url, params=payload, headers=headers, verify=False, timeout=timeout)
                self.log(f"Get Groups - Response Status: {response.status_code}")
                self.log(f"Get Groups - Response URL: {response.url}")
                self.log(f"Get Groups - Full URL with params: {response.url}")
            else:
                response = requests.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
                self.log(f"Response Status: {response.status_code}")
            
            # Check for HTTP errors before raise_for_status
            if response.status_code >= 400:
                try:
                    error_response = response.json()
                    self.log(f"Error Response: {error_response}")
                except:
                    error_response = response.text
                    self.log(f"Error Response (text): {error_response}")
                
                # Provide specific error messages based on status code
                if response.status_code == 500:
                    error_msg = f"Server error (500): The Z-API server encountered an internal error. This may indicate: invalid payload format, missing required fields, or server-side issues. Payload sent: {payload}. Response: {error_response if isinstance(error_response, str) else error_response}"
                elif response.status_code == 400:
                    error_msg = f"Bad request (400): Invalid request parameters. Response: {error_response if isinstance(error_response, str) else error_response}"
                elif response.status_code == 401:
                    error_msg = f"Unauthorized (401): Invalid authentication token or client token. Response: {error_response if isinstance(error_response, str) else error_response}"
                elif response.status_code == 404:
                    error_msg = f"Not found (404): Instance or endpoint not found. Check instance ID and token. Response: {error_response if isinstance(error_response, str) else error_response}"
                else:
                    error_msg = f"HTTP {response.status_code} error: {error_response if isinstance(error_response, str) else error_response}"
                
                result = {
                    "error": error_msg,
                    "error_type": f"http_{response.status_code}",
                    "status_code": response.status_code,
                    "payload_sent": payload,
                    "api_response": error_response,
                }
            else:
                response.raise_for_status()
                result = response.json()
                if message_type == "Get Groups":
                    self.log(f"Get Groups - Response Data: {result}")
                    # Verificar se há dados na resposta
                    if isinstance(result, dict):
                        groups = result.get('groups', [])
                        total = result.get('total', 0)
                        self.log(f"Get Groups - Total groups: {total}, Groups in response: {len(groups) if isinstance(groups, list) else 'N/A'}")
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if "Failed to resolve" in error_str or "NameResolutionError" in error_str:
                error_msg = f"DNS resolution failed: Cannot resolve hostname 'api.z-api.io'. Please check your internet connection and DNS settings."
            else:
                error_msg = f"Connection error: {error_str}"
            self.log(error_msg)
            result = {
                "error": error_msg,
                "error_type": "connection_error",
                "input": {
                    "url": url,
                    "instance": instance,
                    "token": token,
                    "client_token": client_token[:10] + "..." if client_token else None,
                    "phone": phone,
                    "message_type": message_type or "unknown",
                },
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout: The request took longer than 30 seconds to complete."
            self.log(error_msg)
            result = {
                "error": error_msg,
                "error_type": "timeout",
                "input": {
                    "url": url,
                    "message_type": message_type or "unknown",
                },
            }
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL error: {str(e)}"
            self.log(error_msg)
            result = {
                "error": error_msg,
                "error_type": "ssl_error",
                "input": {
                    "url": url,
                    "message_type": message_type or "unknown",
                },
            }
        except ValueError as e:
            error_msg = f"Validation error: {str(e)}"
            self.log(error_msg)
            result = {
                "error": error_msg,
                "error_type": "validation_error",
                "input": {
                    "url": url,
                    "phone": phone,
                    "message_type": message_type or "unknown",
                    "message": getattr(self, 'message', None),
                },
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.log(error_msg)
            result = {
                "error": error_msg,
                "error_type": "request_error",
                "input": {
                    "url": url,
                    "instance": instance,
                    "token": token,
                    "client_token": client_token[:10] + "..." if client_token else None,
                    "phone": phone,
                    "message_type": message_type or "unknown",
                    "message": getattr(self, 'message', None),
                    "audio": getattr(self, 'audio', None),
                    "image": getattr(self, 'image', None),
                    "image_caption": getattr(self, 'image_caption', None),
                    "video": getattr(self, 'video', None),
                    "caption": getattr(self, 'caption', None),
                    "document": getattr(self, 'document', None),
                    "fileName": getattr(self, 'fileName', None),
                    "extension": getattr(self, 'extension', None),
                    "buttonList": getattr(self, 'buttonList', None),
                    "page": getattr(self, 'page', None),
                    "pageSize": getattr(self, 'pageSize', None),
                },
            }

        # Para Get Groups, vamos garantir que a resposta seja processada corretamente
        if message_type == "Get Groups":
            self.log(f"Processing Get Groups response: {result}")
            self.log(f"Response type: {type(result)}")
            
            # Verificar se a resposta tem a estrutura esperada
            if isinstance(result, dict):
                self.log(f"Response keys: {list(result.keys())}")
                
                # Se a API retorna os grupos diretamente
                if 'groups' in result:
                    groups_data = result['groups']
                    self.log(f"Get Groups - Found {len(groups_data) if isinstance(groups_data, list) else 'N/A'} groups in response")
                # Se a API retorna os grupos em uma estrutura diferente
                elif 'data' in result and isinstance(result['data'], list):
                    groups_data = result['data']
                    self.log(f"Get Groups - Found {len(groups_data)} groups in data field")
                # Se a resposta é uma lista diretamente
                elif isinstance(result, list):
                    groups_data = result
                    self.log(f"Get Groups - Response is a list with {len(groups_data)} items")
                else:
                    # Se não encontrou grupos, usar a resposta completa
                    groups_data = result
                    self.log(f"Get Groups - Using complete response as groups data")
                
                # Garantir que temos uma lista de grupos
                if not isinstance(groups_data, list):
                    groups_data = [groups_data] if groups_data else []
                
                self.log(f"Final groups_data: {groups_data}")
                self.log(f"Final groups_data type: {type(groups_data)}")
                self.log(f"Final groups_data length: {len(groups_data)}")
                
                final_result = {
                    "groups": groups_data,
                    "total": len(groups_data),
                    "page": getattr(self, 'page', 1),
                    "pageSize": getattr(self, 'pageSize', 10),
                    "raw_response": result
                }
            else:
                self.log(f"Response is not a dict, type: {type(result)}")
                if isinstance(result, list):
                    self.log(f"Response is a list, treating as groups data")
                    final_result = {
                        "groups": result,
                        "total": len(result),
                        "page": getattr(self, 'page', 1),
                        "pageSize": getattr(self, 'pageSize', 10),
                        "raw_response": result
                    }
                else:
                    self.log(f"Response is not a dict or list, type: {type(result)}")
                    final_result = {
                        "groups": [],
                        "total": 0,
                        "error": "Invalid response format",
                        "raw_response": result
                    }
        else:
            final_result = result

        # Armazenar o resultado para uso no DataFrame
        if message_type == "Get Groups":
            self._groups_result = final_result
            self.log(f"Stored groups result for DataFrame: {self._groups_result}")
            self.log(f"Groups result type: {type(self._groups_result)}")
            if isinstance(self._groups_result, dict):
                self.log(f"Groups result keys: {list(self._groups_result.keys())}")
                if 'groups' in self._groups_result:
                    self.log(f"Groups count in stored result: {len(self._groups_result['groups']) if isinstance(self._groups_result['groups'], list) else 'N/A'}")
        
        return Data(data={"api_response": final_result})

    def get_groups_dataframe(self) -> DataFrame:
        """
        Gera um DataFrame dinâmico baseado nos dados dos grupos retornados pela API.
        Detecta automaticamente os campos disponíveis e estrutura os dados.
        """
        try:
            # Verificar se a operação atual é Get Groups
            message_type = None
            if hasattr(self, 'type') and self.type:
                if isinstance(self.type, list) and len(self.type) > 0:
                    message_type = self.type[0].get("name")
                elif isinstance(self.type, dict):
                    message_type = self.type.get("name")
                else:
                    message_type = self.type
            
            self.log(f"Current operation type: {message_type}")
            
            if message_type != "Get Groups":
                self.log("Not a Get Groups operation, returning empty DataFrame")
                return DataFrame([])
            
            # Verificar se temos dados de grupos
            self.log(f"Checking for groups data...")
            self.log(f"Has _groups_result: {hasattr(self, '_groups_result')}")
            
            if not hasattr(self, '_groups_result'):
                self.log("No _groups_result attribute found")
                return DataFrame([])
            
            if not self._groups_result:
                self.log("_groups_result is empty or None")
                return DataFrame([])
            
            self.log(f"_groups_result content: {self._groups_result}")
            
            groups_data = self._groups_result.get('groups', [])
            self.log(f"Groups data extracted: {groups_data}")
            self.log(f"Groups data type: {type(groups_data)}")
            self.log(f"Groups data length: {len(groups_data) if isinstance(groups_data, list) else 'N/A'}")
            
            if not groups_data:
                self.log("No groups found in the response")
                return DataFrame([])
            
            # Normalizar os dados dos grupos
            normalized_groups = []
            self.log(f"Starting normalization of {len(groups_data)} groups")
            
            for i, group in enumerate(groups_data):
                self.log(f"Processing group {i+1}: {type(group)} - {group}")
                
                if isinstance(group, dict):
                    # Flatten nested structures
                    flat_group = self._flatten_dict(group)
                    self.log(f"Flattened group {i+1}: {flat_group}")
                    normalized_groups.append(flat_group)
                else:
                    # Se não for dict, criar um registro básico
                    basic_group = {
                        'group_data': str(group),
                        'group_type': type(group).__name__
                    }
                    self.log(f"Basic group {i+1}: {basic_group}")
                    normalized_groups.append(basic_group)
            
            self.log(f"Normalized groups count: {len(normalized_groups)}")
            if not normalized_groups:
                self.log("No valid group data found after normalization")
                return DataFrame([])
            
            # Criar DataFrame
            self.log(f"Creating DataFrame with {len(normalized_groups)} normalized groups")
            df = pd.DataFrame(normalized_groups)
            self.log(f"DataFrame created, shape: {df.shape}")
            
            # Se o DataFrame está vazio, criar um DataFrame com informações básicas
            if df.empty:
                self.log("DataFrame is empty, creating basic structure")
                df = pd.DataFrame([{
                    'status': 'no_groups_found',
                    'message': 'No groups data available or API returned empty response',
                    'timestamp': pd.Timestamp.now().isoformat()
                }])
            
            # Formatar colunas para melhor legibilidade
            df = self._format_dataframe_columns(df)
            
            # Adicionar informações de paginação e metadados
            if hasattr(self, '_groups_result'):
                metadata = {
                    'total_groups': self._groups_result.get('total', 0),
                    'current_page': self._groups_result.get('page', 1),
                    'page_size': self._groups_result.get('pageSize', 10),
                    'groups_in_page': len(normalized_groups)
                }
                
                # Adicionar colunas de metadados
                for key, value in metadata.items():
                    df[key] = value
                
                self.log(f"Added metadata: {metadata}")
            
            # Log das colunas encontradas
            self.log(f"Final DataFrame columns: {list(df.columns)}")
            self.log(f"Final DataFrame shape: {df.shape}")
            self.log(f"DataFrame head: {df.head().to_dict() if not df.empty else 'Empty DataFrame'}")
            
            return DataFrame(df)
            
        except Exception as e:
            self.log(f"Error creating DataFrame: {str(e)}")
            return DataFrame([])
    
    def _flatten_dict(self, data, parent_key='', sep='_'):
        """
        Flatten nested dictionaries for better DataFrame structure.
        """
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Para listas, juntar elementos com vírgula
                if v and isinstance(v[0], dict):
                    # Se a lista contém dicionários, flatten cada um
                    flattened_items = []
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            flattened = self._flatten_dict(item, f"{new_key}_{i}", sep=sep)
                            flattened_items.append(flattened)
                    if flattened_items:
                        # Combinar todos os campos dos itens flattenados
                        combined = {}
                        for item in flattened_items:
                            combined.update(item)
                        items.extend(combined.items())
                else:
                    items.append((new_key, ', '.join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _infer_schema(self, sample_data):
        """
        Infere o schema dos dados baseado em uma amostra.
        """
        schema = {}
        
        if isinstance(sample_data, dict):
            for key, value in sample_data.items():
                schema[key] = {
                    "type": type(value).__name__,
                    "description": f"Campo: {key}"
                }
        
        return schema
    
    def _format_dataframe_columns(self, df):
        """
        Formata as colunas do DataFrame para melhor legibilidade.
        """
        if df.empty:
            return df
        
        # Renomear colunas para melhor legibilidade
        column_mapping = {
            'id': 'group_id',
            'name': 'group_name',
            'description': 'group_description',
            'created_at': 'created_date',
            'updated_at': 'updated_date',
            'member_count': 'total_members',
            'admin_count': 'total_admins'
        }
        
        # Aplicar renomeação apenas se as colunas existirem
        existing_columns = df.columns.tolist()
        rename_dict = {col: column_mapping[col] for col in existing_columns if col in column_mapping}
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
            self.log(f"Renamed columns: {rename_dict}")
        
        return df
