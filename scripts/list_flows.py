#!/usr/bin/env python3
"""
Script to list all flows from Langflow installation with pagination support.

Usage:
    python list_flows.py

Requirements:
    pip install requests python-dotenv
"""

import os
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv


class LangflowFlowsList:
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
    
    def get_flows(self, page=1, size=50, remove_example_flows=True, 
                  components_only=False, get_all=True, header_flows=False):
        """Get list of flows with pagination and filtering options"""
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
            
            self.log(f"Fetching flows from: {url}")
            self.log(f"Parameters: page={page}, size={size}, remove_example_flows={remove_example_flows}, "
                    f"components_only={components_only}, get_all={get_all}, header_flows={header_flows}")
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            flows = response.json()
            self.log(f"Found {len(flows)} flows on page {page}")
            return flows
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching flows: {e}")
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
    
    def get_all_flows_paginated(self, page_size=50, remove_example_flows=True,
                                components_only=False, header_flows=False):
        """Get all flows using pagination"""
        all_flows = []
        page = 1
        max_pages = 100  # Safety limit to prevent infinite loops
        
        self.log(f"Starting paginated flow retrieval (page_size={page_size})")
        
        while page <= max_pages:
            flows = self.get_flows(
                page=page,
                size=page_size,
                remove_example_flows=remove_example_flows,
                components_only=components_only,
                get_all=True,
                header_flows=header_flows
            )
            
            if not flows:
                break
            
            # Check for duplicate flows (in case API is returning same flows)
            new_flows = []
            for flow in flows:
                if not any(existing_flow.get('id') == flow.get('id') for existing_flow in all_flows):
                    new_flows.append(flow)
            
            if not new_flows:
                self.log(f"⚠️  No new flows found on page {page}. Stopping pagination.")
                break
            
            all_flows.extend(new_flows)
            self.log(f"Retrieved {len(new_flows)} new flows from page {page} (total: {len(all_flows)})")
            
            # If we got fewer flows than requested, we've reached the end
            if len(flows) < page_size:
                break
            
            # If we got exactly page_size flows, continue to next page
            # The API might be returning more flows than requested
            if len(flows) == page_size:
                # Continue to next page
                pass
            
            page += 1
        
        if page > max_pages:
            self.log(f"⚠️  Reached maximum page limit ({max_pages}). Stopping pagination.")
        
        self.log(f"Total flows retrieved: {len(all_flows)}")
        return all_flows
    
    def display_flows(self, flows, show_details=False):
        """Display flows in a formatted way"""
        if not flows:
            self.log("No flows found.")
            return
        
        print(f"\n📋 Langflow Flows ({len(flows)} found)")
        print("=" * 80)
        
        for i, flow in enumerate(flows, 1):
            flow_id = flow.get('id', 'N/A')
            name = flow.get('name', 'N/A')
            description = flow.get('description', 'No description')
            created_at = flow.get('created_at', 'N/A')
            updated_at = flow.get('updated_at', 'N/A')
            is_active = flow.get('is_active', 'N/A')
            project_id = flow.get('project_id', 'N/A')
            
            print(f"\n{i}. Flow Details:")
            print(f"   ID: {flow_id}")
            print(f"   Name: {name}")
            print(f"   Active: {is_active}")
            print(f"   Project ID: {project_id}")
            
            if show_details:
                print(f"   Description: {description}")
                print(f"   Created: {created_at}")
                print(f"   Updated: {updated_at}")
                
                # Show additional fields if they exist
                for key, value in flow.items():
                    if key not in ['id', 'name', 'description', 'created_at', 'updated_at', 'is_active', 'project_id']:
                        print(f"   {key.title()}: {value}")
            else:
                if description and description != 'No description':
                    print(f"   Description: {description}")
            
            print("-" * 40)
        
        print(f"\n💡 Tip: Use --show-details to see all flow information")
    
    def export_flows_json(self, flows, output_file="flows_list.json"):
        """Export flows list to JSON file"""
        try:
            import json
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(flows, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Flows exported to: {output_file}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error exporting to JSON: {e}")
            return False
    
    def get_flow_details(self, flow_id):
        """Get detailed information about a specific flow"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/{flow_id}"
            self.log(f"Fetching details for flow {flow_id}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            flow_details = response.json()
            self.log(f"✅ Retrieved details for flow: {flow_details.get('name', 'N/A')}")
            return flow_details
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching flow details: {e}")
            return None
    
    def list_flows(self, show_details=False, export_json=False, output_file=None,
                   page_size=50, remove_example_flows=True, components_only=False,
                   header_flows=False, get_specific_flow=None):
        """Main method to list flows"""
        self.log("Starting Langflow flows listing...")
        
        if get_specific_flow:
            # Get details for a specific flow
            flow_details = self.get_flow_details(get_specific_flow)
            if flow_details:
                self.display_flows([flow_details], show_details=True)
                if export_json:
                    output_file = output_file or f"flow_{get_specific_flow}_details.json"
                    self.export_flows_json([flow_details], output_file)
                return True
            else:
                return False
        else:
            # Get all flows
            flows = self.get_all_flows_paginated(
                page_size=page_size,
                remove_example_flows=remove_example_flows,
                components_only=components_only,
                header_flows=header_flows
            )
            
            if not flows:
                self.log("No flows found or connection error")
                return False
            
            # Display flows
            self.display_flows(flows, show_details)
            
            # Export to JSON if requested
            if export_json:
                output_file = output_file or "flows_list.json"
                self.export_flows_json(flows, output_file)
            
            return True


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="List Langflow flows")
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
        help="Show detailed flow information"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export flows list to JSON file"
    )
    parser.add_argument(
        "--output-file",
        default="flows_list.json",
        help="Output file name for JSON export (default: flows_list.json)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Number of flows per page (default: 50)"
    )
    parser.add_argument(
        "--include-example-flows",
        action="store_true",
        help="Include example flows in results (default: exclude example flows)"
    )
    parser.add_argument(
        "--components-only",
        action="store_true",
        help="Return only flow components"
    )
    parser.add_argument(
        "--header-flows",
        action="store_true",
        help="Include header flows"
    )
    parser.add_argument(
        "--flow-id",
        help="Get details for a specific flow ID"
    )
    
    args = parser.parse_args()
    
    # Initialize lister
    lister = LangflowFlowsList(args.langflow_url, args.langflow_token)
    
    # List flows
    success = lister.list_flows(
        show_details=args.show_details,
        export_json=args.export_json,
        output_file=args.output_file,
        page_size=args.page_size,
        remove_example_flows=not args.include_example_flows,
        components_only=args.components_only,
        header_flows=args.header_flows,
        get_specific_flow=args.flow_id
    )
    
    if success:
        print("\n✅ Flows listing completed successfully!")
    else:
        print("\n❌ Flows listing failed!")
        exit(1)


if __name__ == "__main__":
    main() 