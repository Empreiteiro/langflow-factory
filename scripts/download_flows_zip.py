#!/usr/bin/env python3
"""
Simple Langflow Flows Download Script
=====================================

This script downloads all flows from a Langflow installation and saves them
as individual JSON files in a local directory.

HOW IT WORKS:
------------
1. Connects to Langflow API and retrieves all available flows
2. Downloads each flow individually as JSON files
3. Saves flows in a timestamped directory
4. Simple and lightweight - no external dependencies beyond requests

FILE STRUCTURE:
--------------
The script creates the following directory structure:
```
./flows_backup/
├── flows_20250101_120000/
│   ├── flow_1.json
│   ├── flow_2.json
│   └── ...
└── flows_20250102_120000/
    ├── flow_1.json
    └── ...
```

CONFIGURATION:
-------------
Environment Variables (.env file):
- LANGFLOW_URL: Your Langflow installation URL
- LANGFLOW_TOKEN: API authentication token

Command Line Arguments:
- --langflow-url: Override Langflow URL
- --langflow-token: Override API token
- --output-dir: Override output directory

USAGE:
-----
# Using environment variables from .env file
python download_flows_zip.py

# With command line arguments
python simple_download_flows.py --langflow-url http://localhost:3000 --langflow-token YOUR_TOKEN

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


class SimpleLangflowDownloader:
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
    
    def get_all_flows(self):
        """Get all available flows from Langflow"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/"
            self.log(f"Fetching flows from: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            flows = response.json()
            if not flows:
                self.log("⚠️  No flows found")
                return []
            
            self.log(f"Found {len(flows)} flows")
            return flows
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error fetching flows: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    self.log("Authentication error. Check if the Langflow token is correct.")
                elif e.response.status_code == 403:
                    self.log("Access denied. Check token permissions.")
            return []
    
    def download_flow(self, flow_id, flow_name=None):
        """Download a specific flow by ID"""
        try:
            url = f"{self.langflow_url}/api/v1/flows/{flow_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            flow_data = response.json()
            return flow_data
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Error downloading flow {flow_id}: {e}")
            return None
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length and remove extra spaces
        filename = filename.strip()[:100]
        
        return filename if filename else "unnamed_flow"
    
    def download_all_flows(self, output_dir="./flows_backup"):
        """Download all flows and save as individual JSON files"""
        self.log("🚀 Starting Langflow flows download...")
        
        # Get all flows
        flows = self.get_all_flows()
        if not flows:
            self.log("❌ No flows found or connection error")
            return False
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        flows_dir = os.path.join(output_dir, f"flows_{timestamp}")
        os.makedirs(flows_dir, exist_ok=True)
        
        self.log(f"📁 Saving flows to: {flows_dir}")
        
        downloaded_count = 0
        failed_count = 0
        
        # Download each flow individually
        for i, flow in enumerate(flows, 1):
            flow_id = flow.get('id')
            flow_name = flow.get('name', f'flow_{i}')
            
            if not flow_id:
                self.log(f"⚠️  Skipping flow {i}: No ID found")
                failed_count += 1
                continue
            
            self.log(f"📥 Downloading flow {i}/{len(flows)}: {flow_name}")
            
            # Download flow data
            flow_data = self.download_flow(flow_id, flow_name)
            
            if flow_data:
                # Sanitize filename
                safe_name = self.sanitize_filename(flow_name)
                filename = f"{safe_name}_{flow_id}.json"
                filepath = os.path.join(flows_dir, filename)
                
                # Save flow data
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(flow_data, f, indent=2, ensure_ascii=False)
                    
                    self.log(f"✅ Saved: {filename}")
                    downloaded_count += 1
                    
                except Exception as e:
                    self.log(f"❌ Error saving {filename}: {e}")
                    failed_count += 1
            else:
                failed_count += 1
        
        # Summary
        self.log("=" * 50)
        self.log(f"📊 Download Summary:")
        self.log(f"   ✅ Successfully downloaded: {downloaded_count}")
        self.log(f"   ❌ Failed downloads: {failed_count}")
        self.log(f"   📁 Saved to: {flows_dir}")
        
        if downloaded_count > 0:
            self.log("🎉 Download completed successfully!")
            return True
        else:
            self.log("❌ No flows were downloaded successfully")
            return False


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Simple Langflow flows downloader")
    parser.add_argument("--langflow-url", 
                       default=os.getenv('LANGFLOW_URL'),
                       help="Langflow installation URL (ex: http://localhost:3000)")
    parser.add_argument("--langflow-token", 
                       default=os.getenv('LANGFLOW_TOKEN'),
                       help="Langflow authentication token (x-api-key)")
    parser.add_argument("--output-dir", 
                       default="./flows_backup",
                       help="Output directory (default: ./flows_backup)")
    
    args = parser.parse_args()
    
    # Validations
    if not args.langflow_url:
        print("❌ Error: LANGFLOW_URL is required. Configure in .env file or use --langflow-url")
        return 1
    
    # Execute download
    downloader = SimpleLangflowDownloader(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token
    )
    
    success = downloader.download_all_flows(output_dir=args.output_dir)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
