#!/usr/bin/env python3
"""
Test GitHub API connectivity and diagnose common issues.
"""

import subprocess
import json
import sys
from datetime import datetime

def run_gh_command(args):
    """Run a gh CLI command and return the result."""
    try:
        result = subprocess.run(
            ['gh'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout, None
    except subprocess.CalledProcessError as e:
        return None, e.stderr
    except FileNotFoundError:
        return None, "gh CLI not found. Please install GitHub CLI."

def test_auth():
    """Test GitHub authentication."""
    print("🔐 Testing GitHub authentication...")
    output, error = run_gh_command(['auth', 'status'])
    
    if error:
        print(f"❌ Authentication failed: {error}")
        return False
    
    print("✅ Authentication successful")
    print(output)
    return True

def test_rate_limit():
    """Check current rate limit status."""
    print("\n📊 Checking rate limits...")
    output, error = run_gh_command(['api', 'rate_limit'])
    
    if error:
        print(f"❌ Failed to check rate limit: {error}")
        return
    
    try:
        data = json.loads(output)
        core = data['resources']['core']
        search = data['resources']['search']
        graphql = data['resources']['graphql']
        
        print(f"Core API: {core['remaining']}/{core['limit']} remaining")
        print(f"Search API: {search['remaining']}/{search['limit']} remaining")
        print(f"GraphQL API: {graphql['remaining']}/{graphql['limit']} remaining")
        
        # Check if any are low
        for name, resource in [('Core', core), ('Search', search), ('GraphQL', graphql)]:
            if resource['remaining'] < resource['limit'] * 0.1:  # Less than 10%
                reset_time = datetime.fromtimestamp(resource['reset'])
                print(f"⚠️  {name} API rate limit is low! Resets at {reset_time}")
                
    except json.JSONDecodeError:
        print("❌ Failed to parse rate limit response")

def test_repo_access(repo):
    """Test access to a specific repository."""
    print(f"\n🔍 Testing access to {repo}...")
    
    # Test basic repo access
    output, error = run_gh_command(['api', f'repos/{repo}', '--jq', '.name'])
    
    if error:
        if "404" in error:
            print(f"❌ Repository not found or no access: {repo}")
        else:
            print(f"❌ Failed to access repository: {error}")
        return False
    
    print(f"✅ Can access repository: {output.strip()}")
    
    # Test issues access
    output, error = run_gh_command(['api', f'repos/{repo}/issues', '--jq', 'length'])
    
    if error:
        print(f"⚠️  Cannot list issues: {error}")
    else:
        print(f"✅ Can list issues (found {output.strip()} open issues)")
    
    return True

def test_graphql():
    """Test GraphQL API access."""
    print("\n🔮 Testing GraphQL API...")
    
    query = '{ viewer { login } }'
    output, error = run_gh_command(['api', 'graphql', '-f', f'query={query}'])
    
    if error:
        print(f"❌ GraphQL API failed: {error}")
        return False
    
    try:
        data = json.loads(output)
        login = data['data']['viewer']['login']
        print(f"✅ GraphQL API working (logged in as {login})")
        return True
    except (json.JSONDecodeError, KeyError):
        print("❌ Failed to parse GraphQL response")
        return False

def main():
    """Run all tests."""
    print("🧪 GitHub API Diagnostic Test\n")
    
    # Test authentication first
    if not test_auth():
        print("\n⚠️  Please run 'gh auth login' to authenticate")
        return 1
    
    # Check rate limits
    test_rate_limit()
    
    # Test GraphQL
    test_graphql()
    
    # Test specific repo if provided
    if len(sys.argv) > 1:
        repo = sys.argv[1]
        test_repo_access(repo)
    else:
        print("\n💡 Tip: Run with a repo name to test specific access")
        print("   Example: python test-github-api.py owner/repo")
    
    print("\n✅ Diagnostic complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())