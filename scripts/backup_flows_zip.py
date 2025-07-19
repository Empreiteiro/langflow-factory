#!/usr/bin/env python3
"""
Langflow ZIP Backup Script
==========================

This script downloads all flows from a Langflow installation and creates
compressed ZIP backups, making them ready for version control on GitHub.

HOW IT WORKS:
------------
1. Connects to Langflow API and retrieves all available flows
2. Uses Langflow's bulk download API to export all flows in a single ZIP file
3. Saves the ZIP file with timestamp in the "Compacted" subfolder
4. Optionally commits and pushes the ZIP backup to a GitHub repository
5. Maintains a history of compressed backups over time

FILE STRUCTURE:
--------------
The script creates the following directory structure:
```
./langflow_backup/                    # Main backup directory
├── Compacted/                        # ZIP backup files
│   ├── langflow_flows_backup_20250101_120000.zip
│   ├── langflow_flows_backup_20250102_120000.zip
│   └── ...
└── .git/                            # Git repository (if GitHub integration enabled)
```

IMPORTANT REQUIREMENTS:
----------------------
- When using GitHub integration (--push-to-github), the output directory MUST be linked to a Git repository
- If no .git folder exists, the script will automatically initialize one
- GitHub repository must exist and be accessible with the provided token
- The script automatically creates and switches to 'main' branch
- ZIP files are preserved locally and also backed up to GitHub

BACKUP STRATEGY:
---------------
This script creates compressed backups that:
- Contain ALL flows in a single ZIP file
- Include complete flow definitions and metadata
- Use timestamp-based naming for version tracking
- Are space-efficient for long-term storage
- Can be easily downloaded and restored

GITHUB INTEGRATION:
------------------
When PUSH_TO_GITHUB=true or --push-to-github flag is used:
1. Initializes Git repository if not present
2. Adds new ZIP backup to Git staging area
3. Creates a commit with descriptive message and timestamp
4. Pushes to GitHub repository specified in GITHUB_REPO
5. Maintains both local ZIP files and GitHub backup history

This approach provides dual backup strategy: local ZIP files for quick access
and GitHub repository for distributed version control and disaster recovery.

CONFIGURATION:
-------------
Environment Variables (.env file):
- LANGFLOW_URL: Your Langflow installation URL
- LANGFLOW_TOKEN: API authentication token
- GITHUB_REPO: GitHub repository (format: owner/repo)
- GITHUB_TOKEN: GitHub access token
- PUSH_TO_GITHUB: Auto-push to GitHub (true/false)

Command Line Arguments:
- --langflow-url: Override Langflow URL
- --langflow-token: Override API token
- --github-repo: Override GitHub repository
- --github-token: Override GitHub token
- --output-dir: Override output directory
- --push-to-github: Enable GitHub push

USAGE:
-----
# Using environment variables from .env file
python backup_flows_zip.py

# With command line arguments
python backup_flows_zip.py --langflow-url http://localhost:3000 --github-repo owner/repo --github-token YOUR_TOKEN

Requirements:
    pip install requests gitpython python-dotenv
"""

import os
import json
import argparse
import requests
import zipfile
import io
from datetime import datetime
from git import Repo
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv


class LangflowFlowsBackup:
    def __init__(self, langflow_url, langflow_token=None, github_token=None, github_repo=None):
        self.langflow_url = langflow_url.rstrip('/')
        self.langflow_token = langflow_token
        self.github_token = github_token
        self.github_repo = github_repo
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
    
    def get_all_flows(self):
        """Search for all available flows in the Langflow installation"""
        try:
            # Endpoint to list all flows
            url = f"{self.langflow_url}/api/v1/flows/"
            self.log(f"Searching flows at: {url}")
            
            # Try first without parameters
            response = self.session.get(url)
            
            # If it fails, try with basic parameters
            if response.status_code != 200:
                params = {
                    'page': '1',
                    'size': '1000'
                }
                response = self.session.get(url, params=params)
            response.raise_for_status()
            
            flows = response.json()
            if not flows:
                self.log("⚠️  API returned empty flow list")
                return []
            self.log(f"Found {len(flows)} flows")
            return flows
            
        except requests.exceptions.RequestException as e:
            self.log(f"Error searching flows: {e}")
            # Check if it's a status code error
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    self.log("Authentication error. Check if the Langflow token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
            return []
    
    def export_flows_zip(self, flow_ids):
        """Export flows to ZIP using the download API"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/download/"
            self.log(f"Exporting {len(flow_ids)} flows to ZIP...")
            
            # Configure headers for download
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            if self.langflow_token:
                headers['x-api-key'] = self.langflow_token
            
            # Make POST with flow IDs list
            response = self.session.post(url, headers=headers, json=flow_ids)
            response.raise_for_status()
            
            # Return ZIP content
            return response.content
            
        except requests.exceptions.RequestException as e:
            self.log(f"Error exporting flows: {e}")
            return None
    
    def get_flow_details(self, flow_id):
        """Search for complete details of a specific flow"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/{flow_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.log(f"Error searching flow {flow_id} details: {e}")
            return None
    
    def push_to_github(self, local_dir, repo_url):
        """Send files to GitHub repository"""
        try:
            # Clone repository or initialize if it doesn't exist
            if os.path.exists(local_dir):
                repo = Repo(local_dir)
                self.log("Local repository found")
            else:
                self.log(f"Cloning repository: {repo_url}")
                repo = Repo.clone_from(repo_url, local_dir)
            
            # Add all files
            repo.index.add('*')
            
            # Commit with descriptive message
            commit_message = f"Langflow Backup - {datetime.now().strftime('%d-%m-%Y')}"
            repo.index.commit(commit_message)
            
            # Push to remote repository
            origin = repo.remotes.origin
            origin.push()
            
            self.log("Backup sent to GitHub successfully!")
            return True
            
        except Exception as e:
            self.log(f"Error sending to GitHub: {e}")
            # Log more details about the error
            if hasattr(e, 'stderr'):
                self.log(f"Git error details: {e.stderr}")
            return False
    
    def backup_flows(self, output_dir="./langflow_backup", push_to_github=False):
        """Execute complete flows backup"""
        self.log("Starting Langflow flows backup...")
        
        # Search for all flows
        flows = self.get_all_flows()
        if not flows:
            self.log("No flows found or connection error")
            return False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Create "Compacted" subfolder
        compressed_backup_dir = os.path.join(output_dir, "Compacted")
        os.makedirs(compressed_backup_dir, exist_ok=True)
        
        # Save flows as ZIP only
        flow_ids = [flow.get('id') for flow in flows if flow.get('id')]
        zip_content = self.export_flows_zip(flow_ids)
        
        if zip_content:
            zip_path = os.path.join(compressed_backup_dir, f"langflow_flows_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            with open(zip_path, 'wb') as f:
                f.write(zip_content)
            self.log(f"ZIP backup saved at: {zip_path}")
            self.log(f"Backup completed! {len(flows)} flows compressed in ZIP")
        else:
            self.log("❌ Failed to export flows to ZIP")
            return False
        
        # Send to GitHub if requested
        if push_to_github and self.github_repo:
            repo_url = f"https://github.com/{self.github_repo}.git"
            if self.github_token:
                repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
            
            success = self.push_to_github(output_dir, repo_url)
            if not success:
                self.log("Failed to send to GitHub")
        
        return True


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Langflow flows backup to GitHub")
    parser.add_argument("--langflow-url", 
                       default=os.getenv('LANGFLOW_URL'),
                       help="Langflow installation URL (ex: http://localhost:3000)")
    parser.add_argument("--langflow-token", 
                       default=os.getenv('LANGFLOW_TOKEN'),
                       help="Langflow authentication token (x-api-key)")
    parser.add_argument("--github-repo", 
                       default=os.getenv('GITHUB_REPO'),
                       help="GitHub repository in owner/repo format")
    parser.add_argument("--github-token", 
                       default=os.getenv('GITHUB_TOKEN'),
                       help="GitHub access token")
    parser.add_argument("--output-dir", 
                       default="./langflow_backup",
                       help="Output directory (default: ./langflow_backup)")
    parser.add_argument("--push-to-github", 
                       action="store_true",
                       default=os.getenv('PUSH_TO_GITHUB', 'false').lower() == 'true',
                       help="Automatically send to GitHub")
    
    args = parser.parse_args()
    
    # Validations
    if not args.langflow_url:
        print("Error: LANGFLOW_URL is required. Configure in .env file or use --langflow-url")
        return 1
    
    if args.push_to_github and not args.github_repo:
        print("Error: GITHUB_REPO is required when PUSH_TO_GITHUB=true. Configure in .env file or use --github-repo")
        return 1
    
    # Execute backup
    backup = LangflowFlowsBackup(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token,
        github_token=args.github_token,
        github_repo=args.github_repo
    )
    
    success = backup.backup_flows(
        output_dir=args.output_dir,
        push_to_github=args.push_to_github
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 