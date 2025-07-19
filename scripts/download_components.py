#!/usr/bin/env python3
"""
Script to list all components from Langflow installation and download them as JSON files.

Usage:
    python download_components.py

Requirements:
    pip install requests python-dotenv
"""

import os
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


class LangflowComponentsDownloader:
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
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
    
    def save_component_to_file(self, component, output_dir):
        """Save a single component to JSON file"""
        try:
            component_id = component.get('id', 'unknown')
            component_name = component.get('name', 'unnamed_component')
            
            # Sanitize filename
            safe_name = self.sanitize_filename(component_name)
            
            # Create filename with ID and name
            filename = f"{component_id}_{safe_name}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Save component to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(component, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Saved: {filename}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving component {component_id}: {e}")
            return False
    
    def download_components(self, output_dir="./Components", page_size=50, 
                          remove_example_flows=True, header_flows=False,
                          get_specific_component=None):
        """Main method to download components"""
        self.log("Starting Langflow components download...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        self.log(f"Output directory: {output_dir}")
        
        if get_specific_component:
            # Download specific component
            component_details = self.get_component_details(get_specific_component)
            if component_details:
                success = self.save_component_to_file(component_details, output_dir)
                if success:
                    self.log(f"✅ Component {get_specific_component} downloaded successfully!")
                return success
            else:
                return False
        else:
            # Download all components
            components = self.get_all_components_paginated(
                page_size=page_size,
                remove_example_flows=remove_example_flows,
                header_flows=header_flows
            )
            
            if not components:
                self.log("No components found or connection error")
                return False
            
            # Download each component
            success_count = 0
            for component in components:
                if self.save_component_to_file(component, output_dir):
                    success_count += 1
            
            self.log(f"\n📊 Download Summary:")
            self.log(f"   Total components: {len(components)}")
            self.log(f"   Successfully downloaded: {success_count}")
            self.log(f"   Failed: {len(components) - success_count}")
            self.log(f"   Files saved in: {output_dir}")
            
            return success_count > 0
    
    def create_components_index(self, output_dir="./Components"):
        """Create an index file with all downloaded components"""
        try:
            index_file = os.path.join(output_dir, "components_index.json")
            
            # Collect information about all JSON files in the directory
            components_info = []
            
            for file in os.listdir(output_dir):
                if file.endswith('.json') and file != 'components_index.json':
                    filepath = os.path.join(output_dir, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            component_data = json.load(f)
                        
                        components_info.append({
                            'filename': file,
                            'id': component_data.get('id', 'N/A'),
                            'name': component_data.get('name', 'N/A'),
                            'type': component_data.get('type', 'N/A'),
                            'description': component_data.get('description', 'No description'),
                            'created_at': component_data.get('created_at', 'N/A'),
                            'updated_at': component_data.get('updated_at', 'N/A'),
                            'is_active': component_data.get('is_active', 'N/A'),
                            'project_id': component_data.get('project_id', 'N/A')
                        })
                    except Exception as e:
                        self.log(f"⚠️  Error reading {file}: {e}")
            
            # Save index file
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(components_info, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Components index created: {index_file}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error creating components index: {e}")
            return False


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Download Langflow components as JSON files")
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
        "--output-dir",
        default="./Components",
        help="Output directory for downloaded components (default: ./Components)"
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
        help="Download a specific component by ID"
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Create an index file with all downloaded components"
    )
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = LangflowComponentsDownloader(args.langflow_url, args.langflow_token)
    
    # Download components
    success = downloader.download_components(
        output_dir=args.output_dir,
        page_size=args.page_size,
        remove_example_flows=not args.include_example_flows,
        header_flows=args.header_flows,
        get_specific_component=args.component_id
    )
    
    # Create index if requested
    if success and args.create_index:
        downloader.create_components_index(args.output_dir)
    
    if success:
        print("\n✅ Components download completed successfully!")
    else:
        print("\n❌ Components download failed!")
        exit(1)


if __name__ == "__main__":
    main() 