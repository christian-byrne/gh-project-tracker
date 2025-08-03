#!/usr/bin/env python3
"""Minimal test to see what's happening."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from github_issue_tracker.github_client import GitHubClient
from github_issue_tracker.models import QueryTemplate
import yaml

async def main():
    # Load template
    with open("templates/comfy-subgraph.yaml") as f:
        data = yaml.safe_load(f)
    template = QueryTemplate(**data)
    
    print(f"Testing with template: {template.name}")
    print(f"Conditions: {template.conditions}")
    print(f"Logic: {template.condition_logic}")
    
    # Test fetching
    async with GitHubClient() as client:
        print(f"\nToken: {client.token[:10] if client.token else 'None'}...")
        
        # Force refresh
        issues = await client.fetch_all_issues_async(template, force_refresh=True)
        print(f"\nGot {len(issues)} issues total")
        
        if not issues:
            print("No issues found! Checking individual repos...")
            # Try fetching from just one repo
            for repo in template.repositories[:1]:
                raw_issues = await client.fetch_issues_async(repo, template.state, template.max_age_months)
                print(f"\n{repo.full_name}: {len(raw_issues)} raw issues")
                
                # Check filtering
                matching = [i for i in raw_issues if i.matches_conditions(template.conditions, template.condition_logic)]
                print(f"  After filtering: {len(matching)} matching issues")
                
                if raw_issues and not matching:
                    print(f"  Sample issue: #{raw_issues[0].number} - {raw_issues[0].title}")
                    print(f"  Labels: {[l.name for l in raw_issues[0].labels]}")

if __name__ == "__main__":
    asyncio.run(main())