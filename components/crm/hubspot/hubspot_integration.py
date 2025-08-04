from langflow.custom import Component
from langflow.io import StrInput, DictInput, SecretStrInput, Output, DataInput, IntInput
from langflow.inputs import SortableListInput
from langflow.schema import Data
from langflow.utils.component_utils import set_field_display
import requests
import json


class HubSpotComponent(Component):
    display_name = "HubSpot Integration"
    description = "Perform actions with the HubSpot API including creating deals, companies, contacts, and searching schemas."
    icon = "mdi-briefcase-plus"
    name = "HubSpotComponent"

    inputs = [
        DataInput(
            name="trigger",
            display_name="Trigger",
            info="Trigger to execute the HubSpot action. Connect any component output here to trigger the action.",
            required=False,
        ),
        SecretStrInput(
            name="api_key",
            display_name="HubSpot API Key",
            info="Your HubSpot private app token.",
            required=True,
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="List of actions to perform with HubSpot API.",
            options=[
                {"name": "Create Deal", "icon": "plus"},
                {"name": "Create Company", "icon": "plus"},
                {"name": "Create Contact", "icon": "plus"},
                {"name": "Get Deal", "icon": "info"},
                {"name": "Get Company", "icon": "info"},
                {"name": "Get Contact", "icon": "info"},
                {"name": "List Deals", "icon": "list"},
                {"name": "List Companies", "icon": "list"},
                {"name": "List Contacts", "icon": "list"},
                {"name": "Search Deals", "icon": "search"},
                {"name": "Search Companies", "icon": "search"},
                {"name": "Search Contacts", "icon": "search"},
                {"name": "Update Deal", "icon": "edit"},
                {"name": "Update Company", "icon": "edit"},
                {"name": "Update Contact", "icon": "edit"},
                {"name": "Delete Deal", "icon": "trash"},
                {"name": "Delete Company", "icon": "trash"},
                {"name": "Delete Contact", "icon": "trash"},
                {"name": "Get Deal Properties", "icon": "list"},
                {"name": "Get Company Properties", "icon": "list"},
                {"name": "Get Contact Properties", "icon": "list"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Dynamic inputs per action (initially hidden)
        DictInput(
            name="deal_properties",
            display_name="Deal Properties",
            show=False,
            tool_mode=True,
            is_list=True,
            info="""Dictionary of deal properties. Common properties include:
{
  "dealname": "Q1 2025 Sales Deal",
  "amount": "50000",
  "pipeline": "default",
  "dealstage": "qualifiedtobuy",
  "closedate": "2025-03-31",
  "description": "Enterprise software deal"
}

Get available properties using 'Get Deal Properties' action."""
        ),
        DictInput(
            name="company_properties",
            display_name="Company Properties",
            show=False,
            tool_mode=True,
            info="""Dictionary of company properties. Common properties include:
{
  "name": "Acme Corporation",
  "domain": "acme.com",
  "industry": "Technology",
  "city": "San Francisco",
  "state": "CA",
  "country": "US",
  "phone": "+1-555-0123",
  "description": "Leading software company"
}

Get available properties using 'Get Company Properties' action."""
        ),
        DictInput(
            name="contact_properties",
            display_name="Contact Properties",
            show=False,
            tool_mode=True,
            info="""Dictionary of contact properties. Common properties include:
{
  "firstname": "John",
  "lastname": "Doe",
  "email": "john.doe@company.com",
  "phone": "+1-555-0123",
  "company": "Acme Corporation",
  "jobtitle": "Sales Manager",
  "lifecyclestage": "lead"
}

Get available properties using 'Get Contact Properties' action."""
        ),
        StrInput(
            name="deal_id",
            display_name="Deal ID",
            show=False,
            tool_mode=True,
            info="The ID of the deal. You can get this from 'List Deals' or 'Search Deals' actions."
        ),
        StrInput(
            name="company_id",
            display_name="Company ID",
            show=False,
            tool_mode=True,
            info="The ID of the company. You can get this from 'List Companies' or 'Search Companies' actions."
        ),
        StrInput(
            name="contact_id",
            display_name="Contact ID",
            show=False,
            tool_mode=True,
            info="The ID of the contact. You can get this from 'List Contacts' or 'Search Contacts' actions."
        ),
        StrInput(
            name="search_query",
            display_name="Search Query",
            show=False,
            tool_mode=True,
            info="Search query for deals, companies, or contacts. Use HubSpot's search syntax."
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            show=False,
            tool_mode=True,
            info="Maximum number of results to return (default: 100)."
        ),
    ]

    outputs = [
        Output(name="hubspot_result", display_name="Data", method="run_action")
    ]

    base_url = "https://api.hubapi.com"

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        # Extract action name from the selected action
        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        field_map = {
            "Create Deal": ["deal_properties"],
            "Create Company": ["company_properties"],
            "Create Contact": ["contact_properties"],
            "Get Deal": ["deal_id"],
            "Get Company": ["company_id"],
            "Get Contact": ["contact_id"],
            "List Deals": ["limit"],
            "List Companies": ["limit"],
            "List Contacts": ["limit"],
            "Search Deals": ["search_query", "limit"],
            "Search Companies": ["search_query", "limit"],
            "Search Contacts": ["search_query", "limit"],
            "Update Deal": ["deal_id", "deal_properties"],
            "Update Company": ["company_id", "company_properties"],
            "Update Contact": ["contact_id", "contact_properties"],
            "Delete Deal": ["deal_id"],
            "Delete Company": ["company_id"],
            "Delete Contact": ["contact_id"],
            "Get Deal Properties": [],
            "Get Company Properties": [],
            "Get Contact Properties": [],
        }

        # Hide all dynamic fields first
        for field_name in ["deal_properties", "company_properties", "contact_properties", "deal_id", "company_id", "contact_id", "search_query", "limit"]:
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

    def get_api_key_value(self):
        """Extract API key value from SecretStrInput"""
        api_key_value = self.api_key
        if hasattr(self.api_key, 'get_secret_value'):
            api_key_value = self.api_key.get_secret_value()
        elif isinstance(self.api_key, str):
            api_key_value = self.api_key
        return api_key_value

    def run_action(self) -> Data:
        # Validate required inputs
        if not hasattr(self, 'api_key') or not self.api_key:
            return Data(data={"error": "API key is required"})
        
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

        # Get API key
        api_key = self.get_api_key_value()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Get other inputs
        deal_properties = getattr(self, 'deal_properties', {})
        company_properties = getattr(self, 'company_properties', {})
        contact_properties = getattr(self, 'contact_properties', {})
        deal_id = getattr(self, 'deal_id', None)
        company_id = getattr(self, 'company_id', None)
        contact_id = getattr(self, 'contact_id', None)
        search_query = getattr(self, 'search_query', None)
        limit = getattr(self, 'limit', 100)

        # Handle Message objects for IDs
        for id_field in [deal_id, company_id, contact_id]:
            if hasattr(id_field, 'content'):
                id_field = id_field.content
            elif hasattr(id_field, 'text'):
                id_field = id_field.text
            elif hasattr(id_field, 'message'):
                id_field = id_field.message

        # Handle Message objects for search_query
        if hasattr(search_query, 'content'):
            search_query = search_query.content
        elif hasattr(search_query, 'text'):
            search_query = search_query.text
        elif hasattr(search_query, 'message'):
            search_query = search_query.message

        try:
            self.log(f"Executing HubSpot action: {action_name}")
            
            if action_name == "Create Deal":
                return self.create_deal(headers, deal_properties)
            elif action_name == "Create Company":
                return self.create_company(headers, company_properties)
            elif action_name == "Create Contact":
                return self.create_contact(headers, contact_properties)
            elif action_name == "Get Deal":
                return self.get_deal(headers, deal_id)
            elif action_name == "Get Company":
                return self.get_company(headers, company_id)
            elif action_name == "Get Contact":
                return self.get_contact(headers, contact_id)
            elif action_name == "List Deals":
                return self.list_deals(headers, limit)
            elif action_name == "List Companies":
                return self.list_companies(headers, limit)
            elif action_name == "List Contacts":
                return self.list_contacts(headers, limit)
            elif action_name == "Search Deals":
                return self.search_deals(headers, search_query, limit)
            elif action_name == "Search Companies":
                return self.search_companies(headers, search_query, limit)
            elif action_name == "Search Contacts":
                return self.search_contacts(headers, search_query, limit)
            elif action_name == "Update Deal":
                return self.update_deal(headers, deal_id, deal_properties)
            elif action_name == "Update Company":
                return self.update_company(headers, company_id, company_properties)
            elif action_name == "Update Contact":
                return self.update_contact(headers, contact_id, contact_properties)
            elif action_name == "Delete Deal":
                return self.delete_deal(headers, deal_id)
            elif action_name == "Delete Company":
                return self.delete_company(headers, company_id)
            elif action_name == "Delete Contact":
                return self.delete_contact(headers, contact_id)
            elif action_name == "Get Deal Properties":
                return self.get_deal_properties(headers)
            elif action_name == "Get Company Properties":
                return self.get_company_properties(headers)
            elif action_name == "Get Contact Properties":
                return self.get_contact_properties(headers)
            else:
                return Data(data={"error": f"Invalid or unsupported action: {action_name}"})

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log(error_msg)
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def create_deal(self, headers, properties):
        """Create a new deal"""
        if not properties:
            return Data(data={"error": "Deal properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/deals"
        payload = {"properties": properties}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        deal = response.json()
        self.status = f"Deal created with ID: {deal.get('id')}"
        return Data(data=deal)

    def create_company(self, headers, properties):
        """Create a new company"""
        if not properties:
            return Data(data={"error": "Company properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/companies"
        payload = {"properties": properties}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        company = response.json()
        self.status = f"Company created with ID: {company.get('id')}"
        return Data(data=company)

    def create_contact(self, headers, properties):
        """Create a new contact"""
        if not properties:
            return Data(data={"error": "Contact properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/contacts"
        payload = {"properties": properties}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        contact = response.json()
        self.status = f"Contact created with ID: {contact.get('id')}"
        return Data(data=contact)

    def get_deal(self, headers, deal_id):
        """Get a specific deal"""
        if not self.is_valid_id(deal_id):
            return Data(data={"error": "Deal ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        deal = response.json()
        self.status = f"Deal retrieved: {deal.get('properties', {}).get('dealname', 'N/A')}"
        return Data(data=deal)

    def get_company(self, headers, company_id):
        """Get a specific company"""
        if not self.is_valid_id(company_id):
            return Data(data={"error": "Company ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        company = response.json()
        self.status = f"Company retrieved: {company.get('properties', {}).get('name', 'N/A')}"
        return Data(data=company)

    def get_contact(self, headers, contact_id):
        """Get a specific contact"""
        if not self.is_valid_id(contact_id):
            return Data(data={"error": "Contact ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        contact = response.json()
        self.status = f"Contact retrieved: {contact.get('properties', {}).get('firstname', 'N/A')} {contact.get('properties', {}).get('lastname', 'N/A')}"
        return Data(data=contact)

    def list_deals(self, headers, limit):
        """List deals"""
        url = f"{self.base_url}/crm/v3/objects/deals"
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        deals = response.json()
        self.status = f"Retrieved {len(deals.get('results', []))} deals"
        return Data(data=deals)

    def list_companies(self, headers, limit):
        """List companies"""
        url = f"{self.base_url}/crm/v3/objects/companies"
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        companies = response.json()
        self.status = f"Retrieved {len(companies.get('results', []))} companies"
        return Data(data=companies)

    def list_contacts(self, headers, limit):
        """List contacts"""
        url = f"{self.base_url}/crm/v3/objects/contacts"
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        contacts = response.json()
        self.status = f"Retrieved {len(contacts.get('results', []))} contacts"
        return Data(data=contacts)

    def search_deals(self, headers, search_query, limit):
        """Search deals"""
        if not search_query:
            return Data(data={"error": "Search query is required"})
        
        url = f"{self.base_url}/crm/v3/objects/deals/search"
        payload = {
            "query": search_query,
            "limit": limit
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        deals = response.json()
        self.status = f"Found {len(deals.get('results', []))} deals matching search"
        return Data(data=deals)

    def search_companies(self, headers, search_query, limit):
        """Search companies"""
        if not search_query:
            return Data(data={"error": "Search query is required"})
        
        url = f"{self.base_url}/crm/v3/objects/companies/search"
        payload = {
            "query": search_query,
            "limit": limit
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        companies = response.json()
        self.status = f"Found {len(companies.get('results', []))} companies matching search"
        return Data(data=companies)

    def search_contacts(self, headers, search_query, limit):
        """Search contacts"""
        if not search_query:
            return Data(data={"error": "Search query is required"})
        
        url = f"{self.base_url}/crm/v3/objects/contacts/search"
        payload = {
            "query": search_query,
            "limit": limit
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        contacts = response.json()
        self.status = f"Found {len(contacts.get('results', []))} contacts matching search"
        return Data(data=contacts)

    def update_deal(self, headers, deal_id, properties):
        """Update a deal"""
        if not self.is_valid_id(deal_id):
            return Data(data={"error": "Deal ID is required"})
        if not properties:
            return Data(data={"error": "Deal properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
        payload = {"properties": properties}
        
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        
        deal = response.json()
        self.status = f"Deal updated: {deal.get('properties', {}).get('dealname', 'N/A')}"
        return Data(data=deal)

    def update_company(self, headers, company_id, properties):
        """Update a company"""
        if not self.is_valid_id(company_id):
            return Data(data={"error": "Company ID is required"})
        if not properties:
            return Data(data={"error": "Company properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        payload = {"properties": properties}
        
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        
        company = response.json()
        self.status = f"Company updated: {company.get('properties', {}).get('name', 'N/A')}"
        return Data(data=company)

    def update_contact(self, headers, contact_id, properties):
        """Update a contact"""
        if not self.is_valid_id(contact_id):
            return Data(data={"error": "Contact ID is required"})
        if not properties:
            return Data(data={"error": "Contact properties are required"})
        
        url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
        payload = {"properties": properties}
        
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        
        contact = response.json()
        self.status = f"Contact updated: {contact.get('properties', {}).get('firstname', 'N/A')} {contact.get('properties', {}).get('lastname', 'N/A')}"
        return Data(data=contact)

    def delete_deal(self, headers, deal_id):
        """Delete a deal"""
        if not self.is_valid_id(deal_id):
            return Data(data={"error": "Deal ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        self.status = f"Deal {deal_id} deleted successfully"
        return Data(data={"success": True, "message": f"Deal {deal_id} deleted"})

    def delete_company(self, headers, company_id):
        """Delete a company"""
        if not self.is_valid_id(company_id):
            return Data(data={"error": "Company ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        self.status = f"Company {company_id} deleted successfully"
        return Data(data={"success": True, "message": f"Company {company_id} deleted"})

    def delete_contact(self, headers, contact_id):
        """Delete a contact"""
        if not self.is_valid_id(contact_id):
            return Data(data={"error": "Contact ID is required"})
        
        url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        self.status = f"Contact {contact_id} deleted successfully"
        return Data(data={"success": True, "message": f"Contact {contact_id} deleted"})

    def get_deal_properties(self, headers):
        """Get deal properties schema"""
        url = f"{self.base_url}/crm/v3/properties/deals"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        properties = response.json()
        results = properties.get('results', [])
        
        # Extract only essential information
        simplified_properties = []
        for prop in results:
            simplified_properties.append({
                "name": prop.get("name"),
                "label": prop.get("label"),
                "type": prop.get("type")
            })
        
        self.status = f"Retrieved {len(simplified_properties)} deal properties"
        return Data(data={"properties": simplified_properties})

    def get_company_properties(self, headers):
        """Get company properties schema"""
        url = f"{self.base_url}/crm/v3/properties/companies"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        properties = response.json()
        results = properties.get('results', [])
        
        # Extract only essential information
        simplified_properties = []
        for prop in results:
            simplified_properties.append({
                "name": prop.get("name"),
                "label": prop.get("label"),
                "type": prop.get("type")
            })
        
        self.status = f"Retrieved {len(simplified_properties)} company properties"
        return Data(data={"properties": simplified_properties})

    def get_contact_properties(self, headers):
        """Get contact properties schema"""
        url = f"{self.base_url}/crm/v3/properties/contacts"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        properties = response.json()
        results = properties.get('results', [])
        
        # Extract only essential information
        simplified_properties = []
        for prop in results:
            simplified_properties.append({
                "name": prop.get("name"),
                "label": prop.get("label"),
                "type": prop.get("type")
            })
        
        self.status = f"Retrieved {len(simplified_properties)} contact properties"
        return Data(data={"properties": simplified_properties})
