#!/usr/bin/env python3
"""Direct test of the TUI startup sequence."""

import asyncio
import sys
sys.path.insert(0, '.')

from github_issue_tracker.tui import IssueTrackerApp
from github_issue_tracker.models import QueryTemplate
import yaml

async def test_startup():
    """Test the app startup directly."""
    # Load template first
    with open("templates/comfy-subgraph.yaml") as f:
        data = yaml.safe_load(f)
    template = QueryTemplate(**data)
    print(f"Template loaded: {template.name}")
    print(f"Conditions: {template.conditions}")
    print(f"Logic: {template.condition_logic}")
    
    # Create app instance
    app = IssueTrackerApp("templates/comfy-subgraph.yaml")
    
    # Check initial state
    print(f"\nInitial state:")
    print(f"  issues: {len(app.issues)}")
    print(f"  filtered_issues: {len(app.filtered_issues)}")
    
    # Try loading template
    await app.load_template()
    print(f"\nAfter load_template:")
    print(f"  template: {app.template.name if app.template else 'None'}")
    
    # Try refresh
    print("\nCalling refresh_issues...")
    await app.refresh_issues(force_refresh=True)
    
    print(f"\nAfter refresh:")
    print(f"  issues: {len(app.issues)}")
    print(f"  filtered_issues: {len(app.filtered_issues)}")
    
    # Check if apply_filter was called
    app.apply_filter()
    print(f"\nAfter apply_filter:")
    print(f"  filtered_issues: {len(app.filtered_issues)}")

if __name__ == "__main__":
    asyncio.run(test_startup())