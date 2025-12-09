"""
Generate a report of contributors who closed the most issues in the last 5 weeks.
Shows issues closed per week per user and total for the 5 weeks period.
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict


def get_week_range(date):
    """Get the start (Monday) and end (Sunday) of the week for a given date."""
    # Get Monday of the week
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Get Sunday of the week
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start, week_end


def format_week_label(week_start):
    """Format week label as 'MM/DD - MM/DD'."""
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"


def generate_contributors_report(json_file_path):
    """Generate a report of contributors who closed issues in the last 5 weeks."""
    
    # Load JSON file
    print(f"Loading issues from {json_file_path}...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    
    print(f"Total issues loaded: {len(issues)}")
    
    # Get current date
    today = datetime.now()
    
    # Calculate the last 5 weeks
    weeks = []
    for i in range(5):
        week_date = today - timedelta(weeks=i)
        week_start, week_end = get_week_range(week_date)
        weeks.append({
            'start': week_start,
            'end': week_end,
            'label': format_week_label(week_start),
            'index': i
        })
    
    # Sort weeks by start date (oldest first)
    weeks.sort(key=lambda x: x['start'])
    
    # Dictionary to store issues closed per user per week
    # Structure: {username: {week_index: count, 'total': count}}
    contributors = defaultdict(lambda: defaultdict(int))
    
    # Process issues
    for issue in issues:
        # Only process closed issues
        if issue.get('state') != 'closed' or not issue.get('closed_at'):
            continue
        
        # Parse closed_at
        try:
            closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
        except (ValueError, KeyError):
            continue
        
        # Get the user who closed the issue
        closed_by = issue.get('closed_by')
        if not closed_by:
            continue
        
        # Check if issue was closed in any of the last 5 weeks
        for week in weeks:
            if week['start'] <= closed_at <= week['end']:
                contributors[closed_by][week['index']] += 1
                contributors[closed_by]['total'] += 1
                break
    
    # Sort contributors by total issues closed (descending)
    sorted_contributors = sorted(
        contributors.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )
    
    # Generate report
    print("\n" + "=" * 100)
    print("LANGFLOW CONTRIBUTORS REPORT - ISSUES CLOSED IN LAST 5 WEEKS")
    print("=" * 100)
    print(f"\nReport generated on: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "-" * 100)
    
    # Header row
    header = f"{'Contributor':<25}"
    for week in weeks:
        header += f" {week['label']:<15}"
    header += f" {'Total':<15}"
    print(header)
    print("-" * 100)
    
    # Data rows
    for username, week_data in sorted_contributors:
        row = f"{username:<25}"
        for week in weeks:
            count = week_data.get(week['index'], 0)
            row += f" {count:<15}"
        row += f" {week_data['total']:<15}"
        print(row)
    
    print("-" * 100)
    
    # Summary statistics
    total_closed = sum(data['total'] for _, data in sorted_contributors)
    print(f"\nSUMMARY:")
    print("-" * 100)
    print(f"Total contributors who closed issues: {len(sorted_contributors)}")
    print(f"Total issues closed in last 5 weeks: {total_closed}")
    
    if sorted_contributors:
        top_contributor = sorted_contributors[0]
        print(f"Top contributor: {top_contributor[0]} ({top_contributor[1]['total']} issues)")
    
    print("=" * 100)


if __name__ == "__main__":
    import sys
    import os
    
    # Default file path
    json_file = "langflow_issues.json"
    
    # Allow custom file path as argument
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    # Try to find the file if it doesn't exist at the provided path
    if not os.path.exists(json_file):
        # Try in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_file = os.path.join(script_dir, "langflow_issues.json")
        if os.path.exists(script_file):
            json_file = script_file
        # Try in the reports directory
        elif os.path.exists("reports/langflow_issues.json"):
            json_file = "reports/langflow_issues.json"
        # Try just the filename in current directory
        elif os.path.exists(os.path.basename(json_file)):
            json_file = os.path.basename(json_file)
    
    try:
        generate_contributors_report(json_file)
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        print("Please provide the correct path to the JSON file.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

