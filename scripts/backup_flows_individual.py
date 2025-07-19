#!/usr/bin/env python3
"""
Langflow Individual Flows Backup Script
=======================================

This script downloads all flows from a Langflow installation and saves each flow
as an individual JSON file, making them ready for version control on GitHub.

HOW IT WORKS:
------------
1. Connects to Langflow API and retrieves all available flows
2. Downloads each flow individually as JSON data
3. Saves each flow as a separate .json file in the "Flows" subfolder
4. Optionally commits and pushes changes to a GitHub repository
5. After successful push, cleans up local JSON files to keep the repo organized

FILE STRUCTURE:
--------------
The script creates the following directory structure:
```
./langflow_backup/           # Main backup directory (configurable via OUTPUT_DIR)
├── Flows/                   # Individual flow JSON files (temporary)
│   ├── flow_name_id1.json
│   ├── flow_name_id2.json
│   └── ...
└── .git/                    # Git repository (automatically initialized)
```

IMPORTANT REQUIREMENTS:
----------------------
- The output directory MUST be linked to a Git repository
- If no .git folder exists, the script will automatically initialize one
- GitHub repository must exist and be accessible with the provided token
- The script automatically creates and switches to 'main' branch
- After successful push to GitHub, local JSON files are automatically deleted

GITHUB INTEGRATION:
------------------
When PUSH_TO_GITHUB=true, the script:
1. Initializes Git repository if not present
2. Adds all files to Git staging area
3. Creates a commit with timestamp
4. Pushes to GitHub repository specified in GITHUB_REPO
5. Cleans up local JSON files after successful push

This approach ensures your GitHub repository stays clean while maintaining
a complete backup history through Git commits.

CONFIGURATION:
-------------
Set these environment variables in your .env file:
- LANGFLOW_URL: Your Langflow installation URL
- LANGFLOW_TOKEN: API authentication token
- GITHUB_REPO: GitHub repository (format: owner/repo)
- GITHUB_TOKEN: GitHub access token
- OUTPUT_DIR: Local backup directory (default: ./langflow_backup)
- PUSH_TO_GITHUB: Auto-push to GitHub (true/false)

USAGE:
-----
python backup_flows_individual.py

The script will automatically use environment variables from .env file.
"""

import os
import json
import requests
from datetime import datetime
from git import Repo, GitCommandError
from dotenv import load_dotenv


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_all_flows(langflow_url, langflow_token):
    url = f"{langflow_url.rstrip('/')}/api/v1/flows/"
    headers = {'accept': 'application/json', 'x-api-key': langflow_token}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_flow_json(langflow_url, langflow_token, flow_id):
    url = f"{langflow_url.rstrip('/')}/api/v1/flows/download/"
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'x-api-key': langflow_token}
    resp = requests.post(url, headers=headers, json=[flow_id], timeout=30)
    resp.raise_for_status()
    return resp.json()


def safe_filename(name, flow_id):
    safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    return f"{safe}_{flow_id}.json"


def save_flow(flow_data, output_dir, flow_name, flow_id):
    # Create Flows subfolder
    flows_dir = os.path.join(output_dir, "Flows")
    os.makedirs(flows_dir, exist_ok=True)
    filename = safe_filename(flow_name, flow_id)
    filepath = os.path.join(flows_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(flow_data, f, indent=2, ensure_ascii=False)
    return filepath


def push_to_github(local_dir, github_repo, github_token=None):
    repo_url = f"https://github.com/{github_repo}.git"
    if github_token:
        repo_url = f"https://{github_token}@github.com/{github_repo}.git"
    git_dir = os.path.join(local_dir, '.git')
    if not os.path.exists(git_dir):
        repo = Repo.init(local_dir)
        # Create main branch if it doesn't exist
        if 'main' not in repo.heads:
            repo.git.checkout(b='main')
        else:
            repo.git.checkout('main')
        repo.create_remote('origin', repo_url)
    else:
        repo = Repo(local_dir)
        # Ensure we're on the main branch
        if repo.active_branch.name != 'main':
            if 'main' in repo.heads:
                repo.git.checkout('main')
            else:
                repo.git.checkout(b='main')
    repo.git.add(A=True)
    try:
        repo.index.commit(f"Langflow Backup - {datetime.now().strftime('%d-%m-%Y')}")
    except GitCommandError:
        log('No changes to commit.')
    try:
        repo.git.push('--set-upstream', 'origin', 'main')
    except GitCommandError as e:
        log(f'⚠️  Error pushing: {e}')
    log("Backup sent to GitHub successfully!")


def main():
    load_dotenv()
    langflow_url = os.getenv('LANGFLOW_URL')
    langflow_token = os.getenv('LANGFLOW_TOKEN')
    github_repo = os.getenv('GITHUB_REPO')
    github_token = os.getenv('GITHUB_TOKEN')
    output_dir = os.getenv('OUTPUT_DIR', './langflow_backup')
    push = os.getenv('PUSH_TO_GITHUB', 'false').lower() == 'true'

    if not langflow_url or not langflow_token:
        log('LANGFLOW_URL or LANGFLOW_TOKEN not configured.')
        return

    log('Listing all flows...')
    flows = get_all_flows(langflow_url, langflow_token)
    log(f'Found {len(flows)} flows.')

    for flow in flows:
        flow_id = flow.get('id')
        flow_name = flow.get('name', f'flow_{flow_id}')
        try:
            log(f'Downloading flow: {flow_name} ({flow_id})')
            flow_json = get_flow_json(langflow_url, langflow_token, flow_id)
            filepath = save_flow(flow_json, output_dir, flow_name, flow_id)
            log(f'Saved: {filepath}')
        except Exception as e:
            log(f'❌ Error downloading flow {flow_id}: {e}')

    if push and github_repo:
        push_to_github(output_dir, github_repo, github_token)

        # After push, delete all JSON flow files from Flows subfolder
        flows_dir = os.path.join(output_dir, "Flows")
        deleted_count = 0
        if os.path.exists(flows_dir):
            for filename in os.listdir(flows_dir):
                if filename.endswith('.json'):
                    try:
                        os.remove(os.path.join(flows_dir, filename))
                        deleted_count += 1
                    except Exception as e:
                        log(f'⚠️  Error deleting {filename}: {e}')
        log(f'{deleted_count} JSON files deleted after push.')

    log('Backup completed!')

if __name__ == "__main__":
    main() 