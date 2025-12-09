"""
Generate a simplified report of open and closed issues in the last 5 weeks.
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


def generate_issues_report(json_file_path):
    """Generate a report of open and closed issues in the last 5 weeks."""
    
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
            'opened': 0,
            'closed': 0
        })
    
    # Sort weeks by start date (oldest first)
    weeks.sort(key=lambda x: x['start'])
    
    # Process issues
    for issue in issues:
        # Parse created_at
        try:
            created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        except (ValueError, KeyError):
            continue
        
        # Check if issue was created in any of the last 5 weeks
        for week in weeks:
            if week['start'] <= created_at <= week['end']:
                week['opened'] += 1
                break
        
        # Parse closed_at if exists
        if issue.get('closed_at') and issue['state'] == 'closed':
            try:
                closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                # Check if issue was closed in any of the last 5 weeks
                for week in weeks:
                    if week['start'] <= closed_at <= week['end']:
                        week['closed'] += 1
                        break
            except (ValueError, KeyError):
                pass
    
    # Generate report
    print("\n" + "=" * 70)
    print("LANGFLOW ISSUES REPORT - LAST 5 WEEKS")
    print("=" * 70)
    print(f"\nReport generated on: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "-" * 70)
    print(f"{'Week':<25} {'Opened':<15} {'Closed':<15} {'Net Change':<15}")
    print("-" * 70)
    
    total_opened = 0
    total_closed = 0
    
    for week in weeks:
        net_change = week['opened'] - week['closed']
        net_change_str = f"+{net_change}" if net_change >= 0 else str(net_change)
        print(f"{week['label']:<25} {week['opened']:<15} {week['closed']:<15} {net_change_str:<15}")
        total_opened += week['opened']
        total_closed += week['closed']
    
    print("-" * 70)
    net_total = total_opened - total_closed
    net_total_str = f"+{net_total}" if net_total >= 0 else str(net_total)
    print(f"{'TOTAL (5 weeks)':<25} {total_opened:<15} {total_closed:<15} {net_total_str:<15}")
    print("=" * 70)
    
    # Additional statistics
    print("\nADDITIONAL STATISTICS:")
    print("-" * 70)
    
    # Count current open issues
    open_issues = sum(1 for issue in issues if issue.get('state') == 'open')
    closed_issues = sum(1 for issue in issues if issue.get('state') == 'closed')
    
    print(f"Current open issues (total): {open_issues}")
    print(f"Current closed issues (total): {closed_issues}")
    print(f"Total issues: {len(issues)}")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    # Default file path
    json_file = "langflow_issues.json"
    
    # Allow custom file path as argument
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    try:
        generate_issues_report(json_file)
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        print("Please provide the correct path to the JSON file.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

