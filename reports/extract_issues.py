import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_all_issues(owner, repo):
    """
    Extracts issues using the environment token (if available).
    """
    # Try to get the token from .env file or system environment variables
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("WARNING: No token found in .env. Request limit will be low (60/hour).")
    else:
        print("Token loaded successfully.")

    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    issues = []
    page = 1
    
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"

    print(f"Starting issue extraction for: {owner}/{repo}...")

    while True:
        params = {
            "state": "all",
            "per_page": 100,
            "page": page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            
            # Check if we've reached the end of pages (422 Unprocessable Entity)
            if response.status_code == 422:
                print(f"Reached end of pages at page {page}. No more issues to extract.")
                break
            
            response.raise_for_status()
            
            page_data = response.json()
            
            if not page_data:
                print(f"No more data at page {page}. Extraction complete.")
                break
            
            for item in page_data:
                if "pull_request" not in item:
                    issues.append({
                        "number": item["number"],
                        "title": item["title"],
                        "state": item["state"],
                        "created_at": item["created_at"],
                        "closed_at": item.get("closed_at"),
                        "closed_by": item.get("closed_by", {}).get("login") if item.get("closed_by") else None,
                        "author": item["user"]["login"] if item["user"] else "Unknown",
                        "url": item["html_url"],
                        #"body": item["body"]
                    })
            
            print(f"Page {page} processed. Total accumulated: {len(issues)} issues.")
            page += 1
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            break

    return issues

def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\nFile saved successfully: {filename}")

if __name__ == "__main__":
    OWNER = "langflow-ai"
    REPO = "langflow"
    
    # We no longer pass the token as an argument, the function gets it from .env
    all_issues = get_all_issues(OWNER, REPO)
    
    if all_issues:
        filename = f"{REPO}_issues.json"
        save_to_json(all_issues, filename)
        print(f"Final total of extracted issues: {len(all_issues)}")
    else:
        print("No issues found or execution error.")