#!/usr/bin/env python3
"""
Script to list all components from Langflow installation with pagination support.

Usage:
    python list_components.py

Requirements:
    pip install requests python-dotenv
"""

import os
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv


class LangflowComponentsList:
    def __init__(self, langflow_url, langflow_token=None):
        self.langflow_url = langflow_url.rstrip('/')
        self.langflow_token = langflow_token
        self.session = requests.Session()
        
        # Configure authentication headers if token provided
        if self.langflow_token:
            self.session.headers.update({
                'x-api-key': self.langflow_token,
                'accept': 'application/json'
            })
        
    def log(self, message):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_components(self, page=1, size=50, remove_example_flows=True, 
                      components_only=True, get_all=True, header_flows=False):
        """Get list of components with pagination and filtering options"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/"
            
            # Prepare query parameters
            params = {
                'page': page,
                'size': size,
                'remove_example_flows': str(remove_example_flows).lower(),
                'components_only': str(components_only).lower(),
                'get_all': str(get_all).lower(),
                'header_flows': str(header_flows).lower()
            }
            
            self.log(f"Fetching components from: {url}")
            self.log(f"Parameters: page={page}, size={size}, remove_example_flows={remove_example_flows}, "
                    f"components_only={components_only}, get_all={get_all}, header_flows={header_flows}")
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            components = response.json()
            self.log(f"Found {len(components)} components on page {page}")
            return components
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching components: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    self.log("Authentication error. Check if the Langflow token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
                elif e.response.status_code == 404:
                    self.log("API endpoint not found. Check if the Langflow URL is correct.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}")
            return []
    
    def get_all_components_paginated(self, page_size=50, remove_example_flows=True,
                                    header_flows=False):
        """Get all components using pagination"""
        all_components = []
        page = 1
        max_pages = 100  # Safety limit to prevent infinite loops
        
        self.log(f"Starting paginated component retrieval (page_size={page_size})")
        
        while page <= max_pages:
            components = self.get_components(
                page=page,
                size=page_size,
                remove_example_flows=remove_example_flows,
                components_only=True,
                get_all=True,
                header_flows=header_flows
            )
            
            if not components:
                break
            
            # Check for duplicate components (in case API is returning same components)
            new_components = []
            for component in components:
                if not any(existing_component.get('id') == component.get('id') for existing_component in all_components):
                    new_components.append(component)
            
            if not new_components:
                self.log(f"⚠️  No new components found on page {page}. Stopping pagination.")
                break
            
            all_components.extend(new_components)
            self.log(f"Retrieved {len(new_components)} new components from page {page} (total: {len(all_components)})")
            
            # If we got fewer components than requested, we've reached the end
            if len(components) < page_size:
                break
            
            # If we got exactly page_size components, continue to next page
            # The API might be returning more components than requested
            if len(components) == page_size:
                # Continue to next page
                pass
            
            page += 1
        
        if page > max_pages:
            self.log(f"⚠️  Reached maximum page limit ({max_pages}). Stopping pagination.")
        
        self.log(f"Total components retrieved: {len(all_components)}")
        return all_components
    
    def display_components(self, components, show_details=False):
        """Display components in a formatted way"""
        if not components:
            self.log("No components found.")
            return
        
        print(f"\n🔧 Langflow Components ({len(components)} found)")
        print("=" * 80)
        
        for i, component in enumerate(components, 1):
            component_id = component.get('id', 'N/A')
            name = component.get('name', 'N/A')
            description = component.get('description', 'No description')
            created_at = component.get('created_at', 'N/A')
            updated_at = component.get('updated_at', 'N/A')
            is_active = component.get('is_active', 'N/A')
            project_id = component.get('project_id', 'N/A')
            component_type = component.get('type', 'N/A')
            
            print(f"\n{i}. Component Details:")
            print(f"   ID: {component_id}")
            print(f"   Name: {name}")
            print(f"   Type: {component_type}")
            print(f"   Active: {is_active}")
            print(f"   Project ID: {project_id}")
            
            if show_details:
                print(f"   Description: {description}")
                print(f"   Created: {created_at}")
                print(f"   Updated: {updated_at}")
                
                # Show additional fields if they exist
                for key, value in component.items():
                    if key not in ['id', 'name', 'description', 'created_at', 'updated_at', 'is_active', 'project_id', 'type']:
                        print(f"   {key.title()}: {value}")
            else:
                if description and description != 'No description':
                    print(f"   Description: {description}")
            
            print("-" * 40)
        
        print(f"\n💡 Tip: Use --show-details to see all component information")
    
    def export_components_json(self, components, output_file="components_list.json"):
        """Export components list to JSON file"""
        try:
            import json
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(components, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Components exported to: {output_file}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error exporting to JSON: {e}")
            return False
    
    def get_component_details(self, component_id):
        """Get detailed information about a specific component"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/{component_id}"
            self.log(f"Fetching details for component {component_id}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            component_details = response.json()
            self.log(f"✅ Retrieved details for component: {component_details.get('name', 'N/A')}")
            return component_details
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching component details: {e}")
            return None
    
    def list_components(self, show_details=False, export_json=False, output_file=None,
                       page_size=50, remove_example_flows=True, header_flows=False,
                       get_specific_component=None):
        """Main method to list components"""
        self.log("Starting Langflow components listing...")
        
        if get_specific_component:
            # Get details for a specific component
            component_details = self.get_component_details(get_specific_component)
            if component_details:
                self.display_components([component_details], show_details=True)
                if export_json:
                    output_file = output_file or f"component_{get_specific_component}_details.json"
                    self.export_components_json([component_details], output_file)
                return True
            else:
                return False
        else:
            # Get all components
            components = self.get_all_components_paginated(
                page_size=page_size,
                remove_example_flows=remove_example_flows,
                header_flows=header_flows
            )
            
            if not components:
                self.log("No components found or connection error")
                return False
            
            # Display components
            self.display_components(components, show_details)
            
            # Export to JSON if requested
            if export_json:
                output_file = output_file or "components_list.json"
                self.export_components_json(components, output_file)
            
            return True


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="List Langflow components")
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_URL", "http://localhost:3000"),
        help="Langflow URL (default: from LANGFLOW_URL env var or http://localhost:3000)"
    )
    parser.add_argument(
        "--langflow-token",
        default=os.getenv("LANGFLOW_TOKEN"),
        help="Langflow API token (default: from LANGFLOW_TOKEN env var)"
    )
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed component information"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export components list to JSON file"
    )
    parser.add_argument(
        "--output-file",
        default="components_list.json",
        help="Output file name for JSON export (default: components_list.json)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Number of components per page (default: 50)"
    )
    parser.add_argument(
        "--include-example-flows",
        action="store_true",
        help="Include example flows in results (default: exclude example flows)"
    )
    parser.add_argument(
        "--header-flows",
        action="store_true",
        help="Include header flows"
    )
    parser.add_argument(
        "--component-id",
        help="Get details for a specific component ID"
    )
    
    args = parser.parse_args()
    
    # Initialize lister
    lister = LangflowComponentsList(args.langflow_url, args.langflow_token)
    
    # List components
    success = lister.list_components(
        show_details=args.show_details,
        export_json=args.export_json,
        output_file=args.output_file,
        page_size=args.page_size,
        remove_example_flows=not args.include_example_flows,
        header_flows=args.header_flows,
        get_specific_component=args.component_id
    )
    
    if success:
        print("\n✅ Components listing completed successfully!")
    else:
        print("\n❌ Components listing failed!")
        exit(1)


if __name__ == "__main__":
    main() 