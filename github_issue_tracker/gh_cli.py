"""GitHub CLI integration for faster data fetching."""

import json
import subprocess
from datetime import datetime

from .models import GitHubIssue, GitHubLabel, GitHubUser, Repository


def check_gh_cli() -> bool:
    """Check if GitHub CLI is available and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def fetch_issues_with_cli(repo: Repository, state: str = "open") -> list[GitHubIssue]:
    """Fetch issues using GitHub CLI (much faster than API)."""
    cmd = [
        "gh", "issue", "list",
        "--repo", repo.full_name,
        "--state", state,
        "--limit", "1000",
        "--json", "number,title,body,state,url,createdAt,updatedAt,closedAt,author,assignees,labels,comments"
    ]
    
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"gh cli error: {result.stderr}")
            
        data = json.loads(result.stdout)
        issues = []
        
        for item in data:
            # Convert CLI format to API format
            author_data = item.get("author", {})
            author = GitHubUser(
                login=author_data.get("login", "unknown"),
                id=0,  # CLI doesn't provide ID
                avatar_url=author_data.get("avatarUrl", ""),
                html_url=f"https://github.com/{author_data.get('login', '')}"
            )
            
            labels = []
            for label_data in item.get("labels", []):
                labels.append(GitHubLabel(
                    id=label_data.get("id", 0),
                    name=label_data.get("name", ""),
                    color=label_data.get("color", ""),
                    description=label_data.get("description")
                ))
            
            issue = GitHubIssue(
                id=item["number"],  # Use number as ID for CLI
                number=item["number"],
                title=item["title"],
                body=item.get("body"),
                state=item["state"].lower(),
                html_url=item["url"],
                created_at=datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updatedAt"].replace("Z", "+00:00")),
                closed_at=datetime.fromisoformat(item["closedAt"].replace("Z", "+00:00")) if item.get("closedAt") else None,
                user=author,
                labels=labels,
                repository_url=f"https://api.github.com/repos/{repo.full_name}",
                comments=item.get("comments", 0),
                repository_name=repo.full_name
            )
            issues.append(issue)
            
        return issues
        
    except Exception:
        # Fall back to API if CLI fails
        return []