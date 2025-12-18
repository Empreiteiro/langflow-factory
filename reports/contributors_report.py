"""
Generate a report of contributors who closed the most issues in the last 5 weeks.
Shows issues closed per week per user and total for the 5 weeks period.
"""

import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict


def get_week_range(date):
    """Get the start (Thursday) and end (Wednesday) of the week for a given date."""
    # Get Thursday of the week (weekday 3)
    # Formula: (weekday - 3) % 7 gives days back to Thursday
    days_since_thursday = (date.weekday() - 3) % 7
    week_start = date - timedelta(days=days_since_thursday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Get Wednesday of the week (6 days after Thursday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start, week_end


def format_week_label(week_start):
    """Format week label as 'MM/DD - MM/DD' (Thursday to Wednesday)."""
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"


def generate_contributors_report(json_file_path):
    """Generate a report of contributors who closed issues in the last 5 weeks."""
    
    # Load JSON file
    print(f"Loading issues from {json_file_path}...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    
    print(f"Total issues loaded: {len(issues)}")
    
    # Get current date in UTC (to match the issue dates which are in UTC)
    # Note: datetime.now() returns local time, but we need UTC for comparison
    # Since we're comparing with UTC dates from JSON, we'll use UTC
    today = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for comparison
    # Use yesterday as reference point (counting backwards from yesterday)
    yesterday = today - timedelta(days=1)
    yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Get the week (Thursday to Wednesday) that contains yesterday
    # This will be Week 0 (the most recent week up to yesterday)
    reference_week_start, _ = get_week_range(yesterday)
    
    # Calculate the last 5 weeks starting from the week containing yesterday
    weeks = []
    for i in range(5):
        week_start = reference_week_start - timedelta(weeks=i)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        # Only include weeks that end on or before yesterday (exclude current week if it started today)
        if week_end <= yesterday:
            weeks.append({
                'start': week_start,
                'end': week_end,
                'label': format_week_label(week_start),
                'index': len(weeks)  # Sequential index for included weeks
            })
    
    # If we have fewer than 5 weeks (because current week started today), add more past weeks
    if len(weeks) < 5:
        last_week_start = weeks[-1]['start'] if weeks else reference_week_start
        for i in range(5 - len(weeks)):
            week_start = last_week_start - timedelta(weeks=i + 1)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            weeks.append({
                'start': week_start,
                'end': week_end,
                'label': format_week_label(week_start),
                'index': len(weeks)
            })
    
    # Sort weeks by start date (oldest first)
    weeks.sort(key=lambda x: x['start'])
    
    # Debug: print week ranges
    print(f"\nDEBUG: Today: {today.strftime('%Y-%m-%d %A')}")
    print(f"DEBUG: Yesterday: {yesterday.strftime('%Y-%m-%d %A')}")
    print(f"DEBUG: Reference week start (week containing yesterday): {reference_week_start.strftime('%Y-%m-%d %A')}")
    print("DEBUG: Week ranges:")
    for week in weeks:
        print(f"  Week {week['index']}: {week['start'].strftime('%Y-%m-%d %A')} to {week['end'].strftime('%Y-%m-%d %A')}")
    print()
    
    # Dictionary to store issues closed per user per week
    # Structure: {username: {week_index: count, 'total': count}}
    contributors = defaultdict(lambda: defaultdict(int))
    
    # Debug: track issues
    closed_issues_count = 0
    issues_in_range = 0
    recent_closed_dates = []
    
    # Process issues
    for issue in issues:
        # Only process closed issues
        if issue.get('state') != 'closed' or not issue.get('closed_at'):
            continue
        
        closed_issues_count += 1
        
        # Parse closed_at (UTC format)
        try:
            closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
        except (ValueError, KeyError):
            continue
        
        # Get the user who closed the issue
        closed_by = issue.get('closed_by')
        if not closed_by:
            continue
        
        # Store recent dates for debugging (last 6 weeks to catch edge cases)
        if closed_at >= reference_week_start - timedelta(weeks=6):
            recent_closed_dates.append((closed_at, closed_by, issue.get('number', 'N/A')))
        
        # Check if issue was closed in any of the last 5 weeks
        for week in weeks:
            if week['start'] <= closed_at <= week['end']:
                contributors[closed_by][week['index']] += 1
                contributors[closed_by]['total'] += 1
                issues_in_range += 1
                break
    
    # Debug output
    print(f"DEBUG: Total closed issues: {closed_issues_count}")
    print(f"DEBUG: Issues in last 5 weeks range: {issues_in_range}")
    print(f"DEBUG: Recent closed dates (last 15, sorted by date):")
    for closed_at, closed_by, issue_num in sorted(recent_closed_dates, reverse=True)[:15]:
        # Check which week this should belong to
        week_found = None
        week_details = None
        for week in weeks:
            if week['start'] <= closed_at <= week['end']:
                week_found = week['index']
                week_details = f"{week['start'].strftime('%Y-%m-%d')} to {week['end'].strftime('%Y-%m-%d')}"
                break
        status = f"✓ Week {week_found} ({week_details})" if week_found is not None else "✗ NO MATCH"
        print(f"  Issue #{issue_num}: {closed_at.strftime('%Y-%m-%d %H:%M:%S')} by {closed_by} - {status}")
    print()
    
    # Debug: show what's in contributors dict
    print("DEBUG: Contributors data:")
    for username, week_data in contributors.items():
        print(f"  {username}: {dict(week_data)}")
    print()
    
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

