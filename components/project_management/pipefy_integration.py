from langflow.custom import Component
from langflow.io import StrInput, DictInput, Output, SecretStrInput, DataInput, IntInput
from langflow.inputs import SortableListInput
from langflow.schema import Data
from langflow.utils.component_utils import set_field_display
import requests
import json


class PipefyComponent(Component):
    display_name = "Pipefy Integration"
    description = "Perform actions with the Pipefy API."
    icon = "database"
    name = "PipefyComponent"

    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the Pipefy action. Connect any component output here to trigger the action.",
            required=False,
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            required=True,
            info="Your Pipefy API token."
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="List of actions to perform with Pipefy API.",
            options=[
                {"name": "Create Card", "icon": "plus"},
                {"name": "Get a Card", "icon": "info"},
                {"name": "List Cards", "icon": "list"},
                {"name": "List Pipe Fields", "icon": "list"},
                {"name": "List Pipe Phases", "icon": "list"},
                {"name": "List Cards on Phase", "icon": "list"},
                {"name": "List Table Records", "icon": "table"},
                {"name": "Create a Table Record", "icon": "plus-square"},
                {"name": "Update a Card Field", "icon": "edit"},
                {"name": "Update a Record Field", "icon": "edit"},
                {"name": "Move Card to Phase", "icon": "arrow-right"},
                {"name": "Delete a Card", "icon": "trash"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Dynamic inputs per action (initially hidden)
        StrInput(
            name="pipe_id", 
            display_name="Pipe ID", 
            show=False,
            info="The ID of the pipe. You can find this in the URL when viewing your pipe in Pipefy."
        ),
        DataInput(
            name="fields", 
            display_name="Fields", 
            show=False,
            tool_mode=True,
            info="""Fields data for the card/record. Use one of these formats:

1. Array of fields (recommended):
[
  {
    "field_id": "campaign_title",
    "field_value": "Q1 2025 Marketing Campaign"
  },
  {
    "field_id": "objective",
    "field_value": "Increase brand awareness"
  }
]

2. Object with title and fields:
{
  "title": "Card Title",
  "fields": [
    {
      "field_id": "campaign_title", 
      "field_value": "Q1 2025 Marketing Campaign"
    }
  ]
}

3. For array fields, use arrays:
{
  "field_id": "marketing_tools",
  "field_value": ["Google Ads", "Instagram", "LinkedIn"]
}

4. For user assignment, use user ID:
{
  "field_id": "responsible_user",
  "field_value": "1234567"
}

Get field IDs using 'List Pipe Fields' or 'List Table Fields' actions."""
        ),
        StrInput(
            name="table_id", 
            display_name="Table ID", 
            show=False,
            info="The ID of the table. You can find this in the URL when viewing your table in Pipefy."
        ),
        MessageInput(
            name="card_id", 
            display_name="Card ID", 
            show=False,
            tool_mode=True,
            info="The ID of the card to update. You can get this from 'List Cards' action or from the card URL in Pipefy."
        ),
        StrInput(
            name="record_id", 
            display_name="Record ID", 
            show=False,
            info="The ID of the table record to update. You can find this in the record URL in Pipefy."
        ),
        StrInput(
            name="field_id", 
            display_name="Field ID", 
            tool_mode=True, 
            show=False,
            info="The ID of the field to update. Get this from 'List Pipe Fields' or 'List Table Fields' actions."
        ),
        MessageInput(
            name="new_value", 
            display_name="New Value", 
            tool_mode=True, 
            show=False,
            info="The new value for the field. For array fields, use JSON array format like [\"value1\", \"value2\"].",
        ),
        StrInput(
            name="phase_id",
            display_name="Phase ID",
            show=False,
            tool_mode=True,
            info="The ID of the phase. Use 'List Pipe Phases' to get phase IDs."
        ),
        IntInput(
            name="cards_limit",
            display_name="Cards Limit",
            show=False,
            tool_mode=True,
            info="Quantidade máxima de cards a retornar na fase (padrão: 30)."
        ),
    ]

    outputs = [
        Output(name="pipefy_result", display_name="Data", method="run_action")
    ]

    base_url = "https://api.pipefy.com/graphql"

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Create Card": ["pipe_id", "fields"],
            "List Cards": ["pipe_id"],
            "Get a Card": ["card_id"],
            "List Pipe Fields": ["pipe_id"],
            "List Table Records": ["table_id"],
            "Create a Table Record": ["table_id", "fields"],
            "Update a Card Field": ["card_id", "field_id", "new_value"],
            "Update a Record Field": ["record_id", "field_id", "new_value"],
            "Delete a Card": ["card_id"],
            "List Pipe Phases": ["pipe_id"],
            "Move Card to Phase": ["card_id", "phase_id"],
            "List Cards on Phase": ["phase_id", "cards_limit"],
        }

        # Hide all dynamic fields first
        for field_name in ["pipe_id", "fields", "table_id", "card_id", "record_id", "field_id", "new_value", "phase_id", "cards_limit"]:
            if field_name in build_config:
                build_config[field_name]["show"] = False

        # Show fields based on selected action
        if len(selected) == 1 and selected[0] in field_map:
            for field_name in field_map[selected[0]]:
                if field_name in build_config:
                    build_config[field_name]["show"] = True

        return build_config

    def is_valid_id(self, val):
        return val not in [None, "None", "", "null"]

    def run_action(self) -> Data:
        # Validate required inputs
        if not hasattr(self, 'api_token') or not self.api_token:
            return Data(data={"error": "API token is required"})
        
        if not hasattr(self, 'action') or not self.action:
            return Data(data={"error": "Action is required"})

        # Extract action name from the selected action
        action_name = None
        if isinstance(self.action, list) and len(self.action) > 0:
            action_name = self.action[0].get("name")
        elif isinstance(self.action, dict):
            action_name = self.action.get("name")
        
        if not action_name:
            return Data(data={"error": "Invalid action selected"})

        # Get other inputs with proper validation
        pipe_id = getattr(self, 'pipe_id', None)
        fields = getattr(self, 'fields', None)
        table_id = getattr(self, 'table_id', None)
        # Handle Message objects for table_id
        if hasattr(table_id, 'content'):
            table_id = table_id.content
        elif hasattr(table_id, 'text'):
            table_id = table_id.text
        elif hasattr(table_id, 'message'):
            table_id = table_id.message
        self.log(f"Raw table_id: {table_id}")
        
        # Se for string e parecer um JSON, tenta decodificar
        if isinstance(table_id, str) and table_id.strip().startswith("{"):
            try:
                table_id = json.loads(table_id)
                self.log(f"table_id after json.loads: {table_id}")
            except Exception as e:
                self.log(f"Failed to decode table_id JSON: {e}")
        if isinstance(table_id, dict):
            table_id = table_id.get('text') or table_id.get('id')
        self.log(f"Parsed table_id: {table_id}")
        
        card_id = getattr(self, 'card_id', None)
        self.log(f"Raw card_id: {card_id}")
        
        # Handle Message objects for card_id
        if hasattr(card_id, 'content'):
            card_id = card_id.content
        elif hasattr(card_id, 'text'):
            card_id = card_id.text
        elif hasattr(card_id, 'message'):
            card_id = card_id.message
        
        # Se for string e parecer um JSON, tenta decodificar
        if isinstance(card_id, str) and card_id.strip().startswith("{"):
            try:
                card_id = json.loads(card_id)
                self.log(f"card_id after json.loads: {card_id}")
            except Exception as e:
                self.log(f"Failed to decode card_id JSON: {e}")
        if isinstance(card_id, dict):
            card_id = card_id.get('text') or card_id.get('id')
        self.log(f"Parsed card_id: {card_id}")
        
        record_id = getattr(self, 'record_id', None)
        field_id = getattr(self, 'field_id', None)
        new_value = getattr(self, 'new_value', None)
        
        # Handle Message objects for new_value
        if hasattr(new_value, 'content'):
            new_value = new_value.content
        elif hasattr(new_value, 'text'):
            new_value = new_value.text
        elif hasattr(new_value, 'message'):
            new_value = new_value.message
        
        phase_id = getattr(self, 'phase_id', None)
        
        # Handle Message objects for phase_id
        if hasattr(phase_id, 'content'):
            phase_id = phase_id.content
        elif hasattr(phase_id, 'text'):
            phase_id = phase_id.text
        elif hasattr(phase_id, 'message'):
            phase_id = phase_id.message

        # Validate pipe_id for actions that require it
        pipe_required_actions = ["Create Card", "List Cards", "List Pipe Fields"]
        if action_name in pipe_required_actions:
            if not pipe_id:
                return Data(data={"error": f"Pipe ID is required for action: {action_name}"})

        # Validate table_id for actions that require it
        table_required_actions = ["Create a Table Record"]
        if action_name in table_required_actions:
            if not table_id:
                return Data(data={"error": f"Table ID is required for action: {action_name}"})

        # Validate card_id, field_id, and new_value for Update a Card Field
        if action_name == "Update a Card Field":
            if not card_id:
                return Data(data={"error": "Card ID is required for Update a Card Field action"})
            if not field_id:
                return Data(data={"error": "Field ID is required for Update a Card Field action"})
            if not new_value:
                return Data(data={"error": "New Value is required for Update a Card Field action"})

        # Validate card_id for Delete a Card
        if action_name == "Delete a Card":
            if not card_id:
                return Data(data={"error": "Card ID is required for Delete a Card action"})

        # Validate card_id for Get a Card
        if action_name == "Get a Card":
            if not card_id:
                return Data(data={"error": "Card ID is required for Get a Card action"})

        # Validate phase_id for List Cards on Phase
        if action_name == "List Cards on Phase":
            if not phase_id:
                return Data(data={"error": "Phase ID is required for List Cards on Phase action"})

        # Validate record_id, field_id, and new_value for Update a Record Field
        if action_name == "Update a Record Field":
            if not record_id:
                return Data(data={"error": "Record ID is required for Update a Record Field action"})
            if not field_id:
                return Data(data={"error": "Field ID is required for Update a Record Field action"})
            if not new_value:
                return Data(data={"error": "New Value is required for Update a Record Field action"})

        # Substituir as validações de IDs obrigatórios por:
        if action_name == "Create Card" and not self.is_valid_id(pipe_id):
            return Data(data={"error": "Pipe ID is required and cannot be None or empty."})
        if action_name == "Create a Table Record" and not self.is_valid_id(table_id):
            return Data(data={"error": "Table ID is required and cannot be None or empty."})
        if action_name == "Update a Card Field" and not self.is_valid_id(card_id):
            return Data(data={"error": "Card ID is required and cannot be None or empty."})
        if action_name == "Delete a Card" and not self.is_valid_id(card_id):
            return Data(data={"error": "Card ID is required and cannot be None or empty."})
        if action_name == "Move Card to Phase" and (not self.is_valid_id(card_id) or not self.is_valid_id(phase_id)):
            return Data(data={"error": "Card ID and Phase ID are required and cannot be None or empty."})
        if action_name == "Update a Record Field" and not self.is_valid_id(record_id):
            return Data(data={"error": "Record ID is required and cannot be None or empty."})

        # Setup headers - handle SecretStrInput properly
        api_token_value = self.api_token
        if hasattr(self.api_token, 'get_secret_value'):
            api_token_value = self.api_token.get_secret_value()
        elif isinstance(self.api_token, str):
            api_token_value = self.api_token
        
        headers = {
            "Authorization": f"Bearer {api_token_value}",
            "Content-Type": "application/json"
        }

        # Process fields input
        fields_str = fields
        if hasattr(fields, 'data'):
            fields_str = fields.data
        elif isinstance(fields, str):
            fields_str = fields
        else:
            fields_str = str(fields) if fields else "{}"

        # Convert fields to proper format for Pipefy API
        if action_name in ["Create Card", "Create a Table Record"] and fields_str:
            try:
                # Parse the fields input
                if isinstance(fields_str, str):
                    fields_data = json.loads(fields_str)
                else:
                    fields_data = fields_str
                
                # Convert to Pipefy format
                if isinstance(fields_data, dict):
                    # If it's a dict with title and fields array
                    if "fields" in fields_data and isinstance(fields_data["fields"], list):
                        fields_array = fields_data["fields"]
                    else:
                        # If it's a direct fields array
                        fields_array = [fields_data]
                elif isinstance(fields_data, list):
                    fields_array = fields_data
                else:
                    fields_array = []
                
                # Convert to Pipefy format: [{"field_id": "id", "field_value": "value"}]
                pipefy_fields = []
                for field in fields_array:
                    if isinstance(field, dict) and "field_id" in field and "field_value" in field:
                        pipefy_fields.append({
                            "field_id": field["field_id"],
                            "field_value": field["field_value"]
                        })
                
                fields_str = json.dumps(pipefy_fields)
                
            except Exception as e:
                self.log(f"Error processing fields: {str(e)}")
                return Data(data={"error": f"Invalid fields format: {str(e)}"})

        params = {
            "pipe_id": int(pipe_id) if self.is_valid_id(pipe_id) else None,
            "fields": fields_str,
            "table_id": int(table_id) if self.is_valid_id(table_id) else None,
            "card_id": int(card_id) if self.is_valid_id(card_id) else None,
            "record_id": record_id,
            "field_id": field_id,
            "new_value": new_value,
            "phase_id": int(phase_id) if self.is_valid_id(phase_id) else None
        }

        # Build and execute query
        query = self.build_query(action_name, params)
        if not query:
            return Data(data={"error": f"Invalid or unsupported action: {action_name}"})

        try:
            self.log(f"Executing Pipefy action: {action_name}")
            
            # Prepare request payload
            if action_name == "Create Card":
                # Parse fields for Create Card
                fields_data = []
                if fields_str and fields_str != "{}":
                    try:
                        if isinstance(fields_str, str):
                            fields_data = json.loads(fields_str)
                        else:
                            fields_data = fields_str
                        
                        # Convert to proper format if needed
                        if isinstance(fields_data, dict) and "fields" in fields_data:
                            fields_data = fields_data["fields"]
                        elif not isinstance(fields_data, list):
                            fields_data = [fields_data]
                    except Exception as e:
                        self.log(f"Error parsing fields: {str(e)}")
                        return Data(data={"error": f"Invalid fields format: {str(e)}"})
                
                # Prepare variables for Create Card
                variables = {
                    "input": {
                        "pipe_id": int(pipe_id) if self.is_valid_id(pipe_id) else None,
                        "fields_attributes": fields_data
                    }
                }
                
                # Add title if provided
                if isinstance(fields_str, dict) and "title" in fields_str:
                    variables["input"]["title"] = fields_str["title"]
                
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "Create a Table Record":
                # Parse fields for Create Table Record
                fields_data = []
                if fields_str and fields_str != "{}":
                    try:
                        if isinstance(fields_str, str):
                            fields_data = json.loads(fields_str)
                        else:
                            fields_data = fields_str
                        
                        # Convert to proper format if needed
                        if isinstance(fields_data, dict) and "fields" in fields_data:
                            fields_data = fields_data["fields"]
                        elif not isinstance(fields_data, list):
                            fields_data = [fields_data]
                    except Exception as e:
                        self.log(f"Error parsing fields: {str(e)}")
                        return Data(data={"error": f"Invalid fields format: {str(e)}"})
                
                # Prepare variables for Create Table Record
                variables = {
                    "input": {
                        "table_id": int(table_id) if self.is_valid_id(table_id) else None,
                        "fields_attributes": fields_data
                    }
                }
                
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "Update a Card Field":
                # Prepare variables for updateCardField
                variables = {
                    "input": {
                        "card_id": int(card_id) if self.is_valid_id(card_id) else None,
                        "field_id": field_id,
                        "new_value": new_value
                    }
                }
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "Delete a Card":
                # Prepare variables for deleteCard
                variables = {
                    "input": {
                        "id": int(card_id) if self.is_valid_id(card_id) else None
                    }
                }
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "Update a Record Field":
                # Prepare variables for setTableRecordFieldValue
                variables = {
                    "input": {
                        "table_record_id": int(record_id) if self.is_valid_id(record_id) else None,
                        "field_id": field_id,
                        "value": new_value
                    }
                }
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "List Pipe Phases":
                request_payload = {"query": query}
                
            elif action_name == "Move Card to Phase":
                variables = {
                    "input": {
                        "card_id": int(card_id) if self.is_valid_id(card_id) else None,
                        "destination_phase_id": int(phase_id) if self.is_valid_id(phase_id) else None
                    }
                }
                request_payload = {
                    "query": query,
                    "variables": variables
                }
                
            elif action_name == "List Cards on Phase":
                request_payload = {"query": query}
            
            elif action_name == "Get a Card":
                self.log(f"Executing Get a Card with card_id: {card_id}")
                request_payload = {"query": query}
                self.log(f"Query: {query}")
            
            else:
                # For other actions, use the query directly
                request_payload = {"query": query}
            
            response = requests.post(self.base_url, headers=headers, json=request_payload)
            response.raise_for_status()
            
            result = response.json()
            self.status = f"Successfully executed {action_name}"
            if action_name == "List Table Records":
                try:
                    data = result.get("data", {})
                    records_data = data.get("table_records", {})
                    output_dict = []
                    for edge in records_data.get("edges", []):
                        node = edge.get("node", {})
                        output_dict.append(node)
                    return Data(data={"records": output_dict})
                except Exception as e:
                    self.log(f"Error fetching table records: {str(e)}")
                    return Data(data={"error": str(e)})
            return Data(data=result)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Pipefy API request error: {str(e)}"
            self.log(error_msg)
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log(error_msg)
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def build_query(self, action, params) -> str:
        match action:
            case "Create Card":
                return """
                mutation CreateCard($input: CreateCardInput!) {
                    createCard(input: $input) {
                        card {
                            id
                            title
                        }
                    }
                }
                """
            case "List Cards":
                return f"""
                query {{
                    allCards(pipeId: {params.get('pipe_id')}) {{
                        edges {{
                            node {{ id title current_phase {{ id name }} }}
                        }}
                    }}
                }}
                """
            case "Get a Card":
                return f"""
                query {{
                    card(id: "{params.get('card_id')}") {{
                        title
                        done
                        id
                        updated_at
                    }}
                }}
                """
            case "List Pipe Fields":
                return f"""
                query {{
                    pipe(id: {params.get('pipe_id')}) {{
                        start_form_fields {{
                            id
                            label
                            type
                            description
                            required
                        }}
                        phases {{
                            fields {{
                                id
                                label
                                type
                                description
                                required
                            }}
                        }}
                    }}
                }}
                """

            case "List Table Records":
                return f"""
                query {{
                    table_records(table_id: {params.get('table_id')}) {{
                        edges {{
                            node {{
                                id
                                title
                                done
                                table {{ id }}
                                created_at
                                created_by {{ id }}
                            }}
                        }}
                    }}
                }}
                """
            case "Create a Table Record":
                return """
                mutation CreateTableRecord($input: CreateTableRecordInput!) {
                    createTableRecord(input: $input) {
                        record {
                            id
                            title
                        }
                    }
                }
                """
            case "Update a Card Field":
                return """
                mutation UpdateCardField($input: UpdateCardFieldInput!) {
                    updateCardField(input: $input) {
                        success
                    }
                }
                """
            case "Delete a Card":
                return """
                mutation DeleteCard($input: DeleteCardInput!) {
                    deleteCard(input: $input) {
                        success
                    }
                }
                """
            case "Update a Record Field":
                return """
                mutation SetTableRecordFieldValue($input: SetTableRecordFieldValueInput!) {
                    setTableRecordFieldValue(input: $input) {
                        clientMutationId
                    }
                }
                """
            case "List Pipe Phases":
                return f"""
                query {{
                    pipe(id: {params.get('pipe_id')}) {{
                        phases {{
                            id
                            name
                            cards_count
                        }}
                    }}
                }}
                """
            case "List Cards on Phase":
                return f"""
                query {{
                    phase(id: "{params.get('phase_id')}") {{
                        id
                        name
                        cards(first: {params.get('cards_limit', 30)}) {{
                            edges {{
                                node {{
                                    id
                                    title
                                    done
                                    created_at
                                    updated_at
                                    current_phase {{
                                        id
                                        name
                                    }}
                                    assignees {{
                                        name
                                        email
                                    }}
                                    fields {{
                                        name
                                        value
                                        filled_at
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
                """
            case "Move Card to Phase":
                return f"""
                mutation {{
                    moveCardToPhase(input: {{
                        card_id: {params.get('card_id')},
                        destination_phase_id: {params.get('phase_id')}
                    }}) {{
                        card {{
                            id
                            title
                            current_phase {{ id name }}
                        }}
                        clientMutationId
                    }}
                }}
                """
            case _:
                return None