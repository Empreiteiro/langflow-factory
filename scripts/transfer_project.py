#!/usr/bin/env python3
"""
Script to transfer a specific project from one Langflow installation to another.

This script will:
1. Download all flows from the specified project in the source installation
2. Upload each flow to the target installation and project

Usage:
    python transfer_project.py --source-project-id PROJECT_ID --target-project-id PROJECT_ID

Requirements:
    pip install requests python-dotenv
"""

import os
import json
import argparse
import requests
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


class LangflowProjectTransfer:
    def __init__(self, source_url, source_token, target_url, target_token):
        self.source_url = source_url.rstrip('/')
        self.source_token = source_token
        self.target_url = target_url.rstrip('/')
        self.target_token = target_token
        
        # Create separate sessions for source and target
        self.source_session = requests.Session()
        self.target_session = requests.Session()
        
        # Configure source authentication headers
        if self.source_token:
            self.source_session.headers.update({
                'x-api-key': self.source_token,
                'accept': 'application/json'
            })
        
        # Configure target authentication headers
        if self.target_token:
            self.target_session.headers.update({
                'x-api-key': self.target_token,
                'accept': 'application/json'
            })
        
    def log(self, message):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_project_flows(self, project_id, langflow_url, session):
        """Get all flows from a specific project"""
        try:
            url = f"{langflow_url}/api/v1/flows/"
            
            # Prepare query parameters to get flows from specific project
            params = {
                'page': 1,
                'size': 100,  # Get more flows per page
                'remove_example_flows': 'true',
                'components_only': 'false',
                'get_all': 'true',
                'header_flows': 'false'
            }
            
            self.log(f"Fetching flows from project {project_id} at: {url}")
            
            all_flows = []
            page = 1
            max_pages = 50  # Safety limit
            
            while page <= max_pages:
                params['page'] = page
                
                response = session.get(url, params=params)
                response.raise_for_status()
                
                flows = response.json()
                if not flows:
                    break
                
                # Filter flows that belong to the specified project
                project_flows = [flow for flow in flows if flow.get('project_id') == project_id]
                all_flows.extend(project_flows)
                
                self.log(f"Found {len(project_flows)} flows from project {project_id} on page {page}")
                
                # If we got fewer flows than requested, we've reached the end
                if len(flows) < params['size']:
                    break
                
                page += 1
            
            self.log(f"Total flows found in project {project_id}: {len(all_flows)}")
            return all_flows
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching flows from project {project_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    self.log("Authentication error. Check if the source token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
                elif e.response.status_code == 404:
                    self.log("API endpoint not found. Check if the source URL is correct.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            self.log(f"❌ Unexpected error fetching flows: {e}")
            return []
    
    def download_flow(self, flow_id, langflow_url, session):
        """Download a specific flow as JSON"""
        try:
            url = f"{langflow_url}/api/v1/flows/{flow_id}"
            self.log(f"Downloading flow {flow_id}")
            
            response = session.get(url)
            response.raise_for_status()
            
            flow_data = response.json()
            self.log(f"✅ Downloaded flow: {flow_data.get('name', 'N/A')}")
            return flow_data
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error downloading flow {flow_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    self.log(f"Flow {flow_id} not found.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            self.log(f"❌ Unexpected error downloading flow {flow_id}: {e}")
            return None
    
    def upload_flow(self, flow_data, target_project_id):
        """Upload a flow to the target installation"""
        try:
            # Create temporary JSON file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                json.dump(flow_data, temp_file, ensure_ascii=False, indent=2)
                temp_file_path = temp_file.name
            
            # Prepare upload URL
            url = f"{self.target_url}/api/v1/flows/upload/"
            if target_project_id:
                url += f"?project_id={target_project_id}"
            
            self.log(f"Uploading flow to: {url}")
            
            # Prepare headers
            headers = {
                'accept': 'application/json'
            }
            if self.target_token:
                headers['x-api-key'] = self.target_token
            
            # Upload the file
            with open(temp_file_path, 'rb') as f:
                files = {
                    'file': (f"flow_{flow_data.get('id', 'unknown')}.json", f, 'application/json')
                }
                
                response = self.target_session.post(url, headers=headers, files=files)
                response.raise_for_status()
            
            result = response.json()
            self.log(f"✅ Flow uploaded successfully!")
            self.log(f"   New Flow ID: {result.get('id', 'N/A')}")
            self.log(f"   Flow Name: {result.get('name', 'N/A')}")
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error uploading flow: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 400:
                    self.log("Bad request. Check if the flow data is compatible with target Langflow.")
                elif e.response.status_code == 401:
                    self.log("Authentication error. Check if the target token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check target token permissions.")
                elif e.response.status_code == 404:
                    self.log("Target project not found. Check if the target_project_id exists.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error uploading flow: {e}")
            return False
        finally:
            # Clean up temporary file if it still exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def verify_project_exists(self, project_id, langflow_url, session, installation_name):
        """Verify that a project exists"""
        try:
            url = f"{langflow_url}/api/v1/projects/{project_id}"
            self.log(f"Verifying project {project_id} exists in {installation_name}")
            
            response = session.get(url)
            response.raise_for_status()
            
            project_data = response.json()
            self.log(f"✅ Project verified: {project_data.get('name', 'N/A')}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error verifying project {project_id} in {installation_name}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    self.log(f"Project {project_id} not found in {installation_name}.")
                else:
                    self.log(f"HTTP {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error verifying project: {e}")
            return False
    
    def transfer_project(self, source_project_id, target_project_id):
        """Transfer all flows from source project to target project"""
        self.log("🚀 Starting project transfer...")
        
        # Verify source project exists
        if not self.verify_project_exists(source_project_id, self.source_url, self.source_session, "source"):
            self.log("❌ Source project verification failed. Aborting transfer.")
            return False
        
        # Verify target project exists
        if not self.verify_project_exists(target_project_id, self.target_url, self.target_session, "target"):
            self.log("❌ Target project verification failed. Aborting transfer.")
            return False
        
        # Get all flows from source project
        self.log(f"📥 Getting flows from source project {source_project_id}...")
        source_flows = self.get_project_flows(source_project_id, self.source_url, self.source_session)
        
        if not source_flows:
            self.log("❌ No flows found in source project. Nothing to transfer.")
            return False
        
        self.log(f"Found {len(source_flows)} flows to transfer")
        
        # Transfer each flow
        success_count = 0
        failed_count = 0
        
        for i, flow in enumerate(source_flows, 1):
            flow_id = flow.get('id')
            flow_name = flow.get('name', 'Unknown')
            
            self.log(f"\n--- Transferring flow {i}/{len(source_flows)}: {flow_name} (ID: {flow_id}) ---")
            
            # Download flow from source
            flow_data = self.download_flow(flow_id, self.source_url, self.source_session)
            if not flow_data:
                self.log(f"❌ Failed to download flow {flow_name}")
                failed_count += 1
                continue
            
            # Upload flow to target
            if self.upload_flow(flow_data, target_project_id):
                success_count += 1
                self.log(f"✅ Successfully transferred flow: {flow_name}")
            else:
                failed_count += 1
                self.log(f"❌ Failed to upload flow: {flow_name}")
        
        # Summary
        self.log(f"\n📊 Transfer Summary:")
        self.log(f"   Total flows: {len(source_flows)}")
        self.log(f"   Successfully transferred: {success_count}")
        self.log(f"   Failed: {failed_count}")
        
        if success_count > 0:
            self.log(f"✅ Project transfer completed! {success_count} flows transferred successfully.")
            return True
        else:
            self.log(f"❌ Project transfer failed! No flows were transferred.")
            return False


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Transfer a project between Langflow installations")
    parser.add_argument(
        "--source-project-id",
        required=True,
        help="Source project ID to transfer from"
    )
    parser.add_argument(
        "--target-project-id",
        required=True,
        help="Target project ID to transfer to"
    )
    parser.add_argument(
        "--source-url",
        default=os.getenv("LANGFLOW_SOURCE_URL", "http://localhost:3000"),
        help="Source Langflow URL (default: from LANGFLOW_SOURCE_URL env var or http://localhost:3000)"
    )
    parser.add_argument(
        "--source-token",
        default=os.getenv("LANGFLOW_SOURCE_TOKEN"),
        help="Source Langflow API token (default: from LANGFLOW_SOURCE_TOKEN env var)"
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("LANGFLOW_TARGET_URL", "http://localhost:3000"),
        help="Target Langflow URL (default: from LANGFLOW_TARGET_URL env var or http://localhost:3000)"
    )
    parser.add_argument(
        "--target-token",
        default=os.getenv("LANGFLOW_TARGET_TOKEN"),
        help="Target Langflow API token (default: from LANGFLOW_TARGET_TOKEN env var)"
    )
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.source_token:
        parser.error("Source token is required. Set LANGFLOW_SOURCE_TOKEN env var or use --source-token")
    
    if not args.target_token:
        parser.error("Target token is required. Set LANGFLOW_TARGET_TOKEN env var or use --target-token")
    
    # Initialize transfer
    transfer = LangflowProjectTransfer(
        source_url=args.source_url,
        source_token=args.source_token,
        target_url=args.target_url,
        target_token=args.target_token
    )
    
    # Transfer project
    success = transfer.transfer_project(args.source_project_id, args.target_project_id)
    
    if success:
        print("\n✅ Project transfer completed successfully!")
    else:
        print("\n❌ Project transfer failed!")
        exit(1)


if __name__ == "__main__":
    main() 