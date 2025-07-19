#!/usr/bin/env python3
"""
Script to list all projects from Langflow installation.

Usage:
    python list_projects.py

Requirements:
    pip install requests python-dotenv
"""

import os
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv


class LangflowProjectsList:
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
        """Get list of all available projects"""
        try:
            url = f"{self.langflow_url}/api/v1/projects/"
            self.log(f"Fetching projects from: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            projects = response.json()
            self.log(f"Found {len(projects)} projects")
            return projects
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching projects: {e}")
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
    
    def display_projects(self, projects, show_details=False):
        """Display projects in a formatted way"""
        if not projects:
            self.log("No projects found.")
            return
        
        print(f"\n📋 Langflow Projects ({len(projects)} found)")
        print("=" * 80)
        
        for i, project in enumerate(projects, 1):
            project_id = project.get('id', 'N/A')
            name = project.get('name', 'N/A')
            description = project.get('description', 'No description')
            created_at = project.get('created_at', 'N/A')
            updated_at = project.get('updated_at', 'N/A')
            
            print(f"\n{i}. Project Details:")
            print(f"   ID: {project_id}")
            print(f"   Name: {name}")
            
            if show_details:
                print(f"   Description: {description}")
                print(f"   Created: {created_at}")
                print(f"   Updated: {updated_at}")
                
                # Show additional fields if they exist
                for key, value in project.items():
                    if key not in ['id', 'name', 'description', 'created_at', 'updated_at']:
                        print(f"   {key.title()}: {value}")
            else:
                if description and description != 'No description':
                    print(f"   Description: {description}")
            
            print("-" * 40)
        
        print(f"\n💡 Tip: Use --show-details to see all project information")
    
    def export_projects_json(self, projects, output_file="projects_list.json"):
        """Export projects list to JSON file"""
        try:
            import json
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Projects exported to: {output_file}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error exporting to JSON: {e}")
            return False
    
    def list_projects(self, show_details=False, export_json=False, output_file=None):
        """Main method to list projects"""
        self.log("Starting Langflow projects listing...")
        
        # Get projects
        projects = self.get_projects()
        if not projects:
            self.log("No projects found or connection error")
            return False
        
        # Display projects
        self.display_projects(projects, show_details)
        
        # Export to JSON if requested
        if export_json:
            output_file = output_file or "projects_list.json"
            self.export_projects_json(projects, output_file)
        
        return True


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="List Langflow projects")
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
        help="Show detailed project information"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export projects list to JSON file"
    )
    parser.add_argument(
        "--output-file",
        default="projects_list.json",
        help="Output file name for JSON export (default: projects_list.json)"
    )
    
    args = parser.parse_args()
    
    # Initialize lister
    lister = LangflowProjectsList(args.langflow_url, args.langflow_token)
    
    # List projects
    success = lister.list_projects(
        show_details=args.show_details,
        export_json=args.export_json,
        output_file=args.output_file
    )
    
    if success:
        print("\n✅ Projects listing completed successfully!")
    else:
        print("\n❌ Projects listing failed!")
        exit(1)


if __name__ == "__main__":
    main() 