#!/usr/bin/env python3
"""
Script to import flows to Langflow installation from JSON files.

Usage:
    python import_flows.py --flow-file path/to/flow.json --project-id PROJECT_ID

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


class LangflowFlowsImport:
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
    
    def get_projects(self):
        """Get list of available projects"""
        try:
            url = f"{self.langflow_url}/api/v1/projects/"
            self.log(f"Fetching projects from: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            projects = response.json()
            self.log(f"Found {len(projects)} projects")
            return projects
            
        except requests.exceptions.RequestException as e:
            self.log(f"Error fetching projects: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    self.log("Authentication error. Check if the Langflow token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
            return []
    
    def import_flow(self, flow_file_path, project_id=None):
        """Import a flow from JSON file"""
        try:
            # Validate file exists and is JSON
            if not os.path.exists(flow_file_path):
                self.log(f"❌ Flow file not found: {flow_file_path}")
                return False
            
            # Check if file is valid JSON
            try:
                with open(flow_file_path, 'r', encoding='utf-8') as f:
                    flow_data = json.load(f)
                self.log(f"✅ Valid JSON file: {flow_file_path}")
            except json.JSONDecodeError as e:
                self.log(f"❌ Invalid JSON file: {e}")
                return False
            
            # Prepare upload URL
            url = f"{self.langflow_url}/api/v1/flows/upload/"
            if project_id:
                url += f"?project_id={project_id}"
            
            self.log(f"Importing flow to: {url}")
            
            # Prepare headers
            headers = {
                'accept': 'application/json'
            }
            if self.langflow_token:
                headers['x-api-key'] = self.langflow_token
            
            # Prepare file for upload
            with open(flow_file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(flow_file_path), f, 'application/json')
                }
                
                response = self.session.post(url, headers=headers, files=files)
                response.raise_for_status()
            
            result = response.json()
            self.log(f"✅ Flow imported successfully!")
            self.log(f"   Flow ID: {result.get('id', 'N/A')}")
            self.log(f"   Flow Name: {result.get('name', 'N/A')}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error importing flow: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 400:
                    self.log("Bad request. Check if the flow file is compatible with Langflow.")
                elif e.response.status_code == 401:
                    self.log("Authentication error. Check if the Langflow token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
                elif e.response.status_code == 404:
                    self.log("Project not found. Check if the project_id exists.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}")
            return False
    
    def import_multiple_flows(self, flow_directory, project_id=None):
        """Import multiple flows from a directory"""
        try:
            flow_dir = Path(flow_directory)
            if not flow_dir.exists():
                self.log(f"❌ Directory not found: {flow_directory}")
                return False
            
            # Find all JSON files
            json_files = list(flow_dir.glob("*.json"))
            if not json_files:
                self.log(f"❌ No JSON files found in: {flow_directory}")
                return False
            
            self.log(f"Found {len(json_files)} JSON files to import")
            
            success_count = 0
            for json_file in json_files:
                self.log(f"\n--- Importing: {json_file.name} ---")
                if self.import_flow(str(json_file), project_id):
                    success_count += 1
            
            self.log(f"\n📊 Import Summary:")
            self.log(f"   Total files: {len(json_files)}")
            self.log(f"   Successful: {success_count}")
            self.log(f"   Failed: {len(json_files) - success_count}")
            
            return success_count > 0
            
        except Exception as e:
            self.log(f"❌ Error importing multiple flows: {e}")
            return False


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Import flows to Langflow")
    parser.add_argument(
        "--flow-file",
        help="Path to the JSON flow file to import"
    )
    parser.add_argument(
        "--flow-directory",
        help="Directory containing JSON flow files to import"
    )
    parser.add_argument(
        "--project-id",
        help="Target project ID for the flow (optional)"
    )
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
        "--list-projects",
        action="store_true",
        help="List available projects and exit"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.flow_file and not args.flow_directory and not args.list_projects:
        parser.error("Please specify --flow-file, --flow-directory, or --list-projects")
    
    if args.flow_file and args.flow_directory:
        parser.error("Please specify either --flow-file or --flow-directory, not both")
    
    # Initialize importer
    importer = LangflowFlowsImport(args.langflow_url, args.langflow_token)
    
    # List projects if requested
    if args.list_projects:
        projects = importer.get_projects()
        if projects:
            print("\nAvailable Projects:")
            for project in projects:
                print(f"  ID: {project.get('id', 'N/A')} - Name: {project.get('name', 'N/A')}")
        else:
            print("No projects found or error occurred.")
        return
    
    # Import flow(s)
    success = False
    if args.flow_file:
        success = importer.import_flow(args.flow_file, args.project_id)
    elif args.flow_directory:
        success = importer.import_multiple_flows(args.flow_directory, args.project_id)
    
    if success:
        print("\n✅ Import completed successfully!")
    else:
        print("\n❌ Import failed!")
        exit(1)


if __name__ == "__main__":
    main() 