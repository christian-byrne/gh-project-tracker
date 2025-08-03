"""GitHub API client for fetching issues."""

import os
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from rich.console import Console
from rich.progress import Progress

from .disk_cache import DiskCache
from .gh_cli import check_gh_cli, fetch_issues_with_cli
from .logging_config import setup_logging
from .models import GitHubIssue, GitHubLabel, GitHubUser, IssueStatus, QueryTemplate, Repository

console = Console()
USE_GH_CLI = check_gh_cli()

# Cache for API responses (TTL: 10 minutes)
_cache: dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(minutes=10)


def get_cached(key: str) -> Any | None:
    """Get cached value if not expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if datetime.now() - timestamp < CACHE_TTL:
            return value
        else:
            del _cache[key]
    return None


def set_cache(key: str, value: Any) -> None:
    """Set cache value with current timestamp."""
    _cache[key] = (value, datetime.now())


async def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt)
            console.print(f"[yellow]Request failed, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})[/yellow]")
            await asyncio.sleep(delay)


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: str | None = None, use_cache: bool = True):
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token. If not provided, 
                   will try to read from GITHUB_TOKEN env var or gh CLI.
            use_cache: Whether to use disk caching (default: True)
        """
        self.logger = setup_logging()
        
        # Try to get token from multiple sources
        self.token = token or os.getenv("GITHUB_TOKEN") or self._get_gh_cli_token()
        self.use_cache = use_cache
        self.disk_cache = DiskCache() if use_cache else None
        
        self.logger.info("Initializing GitHub client", 
                        use_cache=use_cache, 
                        has_token=bool(self.token),
                        token_prefix=self.token[:10] if self.token else None,
                        use_gh_cli=USE_GH_CLI)
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        # Use async client with longer timeout for poor connections
        self.client = httpx.AsyncClient(
            headers=self.headers, 
            timeout=httpx.Timeout(300.0, connect=30.0),
            limits=httpx.Limits(max_connections=10)
        )
    
    def _get_gh_cli_token(self) -> str | None:
        """Get GitHub token from gh CLI if available."""
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.logger.info("Retrieved token from gh CLI")
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.client.aclose()

    def __enter__(self):
        """Context manager entry for sync usage."""
        return self

    def __exit__(self, *args):
        """Context manager exit for sync usage."""
        # Don't close in sync context - let it be handled by async context
        pass

    async def fetch_issues_async(self, repo: Repository, state: str = "open", max_age_months: int = 12) -> list[GitHubIssue]:
        """Fetch issues from a repository asynchronously.
        
        Args:
            repo: Repository to fetch issues from
            state: Issue state filter (open, closed, all)
            max_age_months: Only fetch issues updated in last N months
            
        Returns:
            List of GitHub issues
        """
        cache_key = f"issues:{repo.full_name}:{state}:{max_age_months}"
        cached = get_cached(cache_key)
        if cached is not None:
            self.logger.info("CACHE HIT - returning cached issues", 
                           repo=repo.full_name, 
                           cached_count=len(cached))
            return list(cached)
        
        # Calculate since date for API filtering
        since_date = datetime.now() - timedelta(days=max_age_months * 30)
        since_iso = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        self.logger.info("FETCHING FRESH ISSUES FROM API", 
                        repo=repo.full_name, 
                        state=state,
                        max_age_months=max_age_months,
                        since_date=since_iso)
        
        # Skip GitHub CLI - it's timing out
        # Just use the API directly with the token we retrieved
                
        issues = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/repos/{repo.full_name}/issues"
            params: dict[str, str | int] = {
                "state": state,
                "page": page,
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc",
                "since": since_iso,
            }
            
            try:
                self.logger.info("MAKING API REQUEST", 
                                url=url, 
                                params=params,
                                page=page)
                
                async def make_request():
                    response = await self.client.get(url, params=params)
                    self.logger.info("API RESPONSE RECEIVED", 
                                   status_code=response.status_code,
                                   headers=dict(response.headers),
                                   repo=repo.full_name,
                                   page=page)
                    response.raise_for_status()
                    return response.json()
                
                page_issues = await retry_with_backoff(make_request)
                
                self.logger.info("API RESPONSE DATA", 
                               repo=repo.full_name,
                               page=page,
                               response_count=len(page_issues) if page_issues else 0)
                
                if not page_issues:
                    self.logger.warning("EMPTY RESPONSE - breaking pagination", 
                                      repo=repo.full_name, page=page)
                    break
                
                self.logger.info("PROCESSING PAGE ISSUES", 
                               page=page, 
                               count=len(page_issues),
                               repo=repo.full_name)
                
                parse_errors = []
                parsed_issues = []
                skipped_prs = 0
                
                for i, issue_data in enumerate(page_issues):
                    try:
                        # Skip pull requests
                        if "pull_request" in issue_data:
                            skipped_prs += 1
                            continue
                        
                        # Log first few issue data structures for debugging
                        if len(issues) + len(parsed_issues) < 3:  # First 3 issues total
                            self.logger.info("SAMPLE ISSUE DATA", 
                                           repo=repo.full_name,
                                           issue_index=i,
                                           issue_number=issue_data.get('number', 'N/A'),
                                           issue_title=issue_data.get('title', 'N/A')[:50],
                                           user_id=issue_data.get('user', {}).get('id', 'N/A'),
                                           user_id_type=type(issue_data.get('user', {}).get('id', None)).__name__)
                        
                        issue = GitHubIssue(**issue_data)
                        issue.repository_name = repo.full_name
                        parsed_issues.append(issue)
                    except Exception as e:
                        parse_errors.append(f"Issue {i}: {str(e)}")
                        continue
                
                if parse_errors:
                    self.logger.error("PARSING ERRORS ON PAGE", 
                                    repo=repo.full_name,
                                    page=page,
                                    error_count=len(parse_errors),
                                    first_few_errors=parse_errors[:3])
                
                issues.extend(parsed_issues)
                
                self.logger.info("PAGE PROCESSED", 
                               repo=repo.full_name,
                               page=page,
                               raw_count=len(page_issues),
                               skipped_prs=skipped_prs,
                               parsed_issues=len(parsed_issues),
                               parse_errors=len(parse_errors),
                               total_issues_so_far=len(issues))
                
                # Check if there are more pages
                if len(page_issues) < per_page:
                    self.logger.info("PAGINATION COMPLETE - last page", 
                                   repo=repo.full_name,
                                   page=page,
                                   returned_count=len(page_issues),
                                   per_page=per_page)
                    break
                    
                page += 1
                
            except httpx.HTTPError as e:
                self.logger.error("HTTP error fetching issues", 
                                repo=repo.full_name,
                                error=str(e),
                                page=page)
                console.print(f"[red]Error fetching issues from {repo.full_name}: {e}[/red]")
                # Don't cache failed requests
                return issues
        
        self.logger.info("API fetch complete", 
                        repo=repo.full_name,
                        total_issues=len(issues),
                        pages_fetched=page-1)
        
        # Cache successful requests
        set_cache(cache_key, issues)
        return issues

    async def fetch_discussions_async(self, repo: Repository) -> list[GitHubIssue]:
        """Fetch discussions from a repository asynchronously using GraphQL.
        
        Args:
            repo: Repository to fetch discussions from
            
        Returns:
            List of discussions as GitHubIssue objects
        """
        cache_key = f"discussions:{repo.full_name}"
        cached = get_cached(cache_key)
        if cached is not None:
            return list(cached)
            
        discussions = []
        cursor = None
        
        query = """
        query($owner: String!, $repo: String!, $cursor: String) {
            repository(owner: $owner, name: $repo) {
                discussions(first: 100, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        number
                        title
                        body
                        createdAt
                        updatedAt
                        closedAt
                        closed
                        url
                        author {
                            login
                            ... on User {
                                id
                                avatarUrl
                                url
                            }
                        }
                        labels(first: 10) {
                            nodes {
                                id
                                name
                                color
                                description
                            }
                        }
                        comments {
                            totalCount
                        }
                    }
                }
            }
        }
        """
        
        while True:
            variables = {
                "owner": repo.owner,
                "repo": repo.repo,
                "cursor": cursor
            }
            
            try:
                async def make_graphql_request():
                    response = await self.client.post(
                        "https://api.github.com/graphql",
                        json={"query": query, "variables": variables}
                    )
                    response.raise_for_status()
                    return response.json()
                
                data = await retry_with_backoff(make_graphql_request)
                if "errors" in data:
                    console.print(f"[red]GraphQL errors for {repo.full_name}: {data['errors']}[/red]")
                    break
                    
                repo_data = data.get("data", {}).get("repository", {})
                discussions_data = repo_data.get("discussions", {})
                
                for disc in discussions_data.get("nodes", []):
                    if not disc:
                        continue
                        
                    # Convert discussion to GitHubIssue format
                    user_data = disc.get("author", {})
                    user = GitHubUser(
                        login=user_data.get("login", "unknown"),
                        id=user_data.get("id", 0) if user_data.get("id") else 0,
                        avatar_url=user_data.get("avatarUrl", ""),
                        html_url=user_data.get("url", "")
                    )
                    
                    labels = []
                    for label_data in disc.get("labels", {}).get("nodes", []):
                        if label_data:
                            labels.append(GitHubLabel(
                                id=int(label_data["id"].split("_")[-1]) if "_" in label_data["id"] else 0,
                                name=label_data["name"],
                                color=label_data["color"],
                                description=label_data.get("description")
                            ))
                    
                    issue = GitHubIssue(
                        id=int(disc["id"].split("_")[-1]) if "_" in disc["id"] else disc["number"],
                        number=disc["number"],
                        title=disc["title"],
                        body=disc.get("body"),
                        state="closed" if disc.get("closed") else "open",
                        html_url=disc["url"],
                        created_at=datetime.fromisoformat(disc["createdAt"].replace("Z", "+00:00")),
                        updated_at=datetime.fromisoformat(disc["updatedAt"].replace("Z", "+00:00")),
                        closed_at=datetime.fromisoformat(disc["closedAt"].replace("Z", "+00:00")) if disc.get("closedAt") else None,
                        user=user,
                        labels=labels,
                        repository_url=f"https://api.github.com/repos/{repo.full_name}",
                        comments=disc.get("comments", {}).get("totalCount", 0),
                        repository_name=repo.full_name,
                        is_discussion=True
                    )
                    
                    discussions.append(issue)
                
                # Check pagination
                page_info = discussions_data.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                    
                cursor = page_info.get("endCursor")
                
            except httpx.HTTPError as e:
                console.print(f"[red]Error fetching discussions from {repo.full_name}: {e}[/red]")
                break
        
        set_cache(cache_key, discussions)
        return discussions


    async def fetch_repo_data_async(self, repo: Repository, template: QueryTemplate, progress_task) -> list[GitHubIssue]:
        """Fetch all data for a single repository."""
        self.logger.info(f"FETCH_REPO_DATA_ASYNC START", repo=repo.full_name)
        
        repo_issues = await self.fetch_issues_async(repo, template.state, template.max_age_months)
        self.logger.info(f"ISSUES FETCHED", repo=repo.full_name, count=len(repo_issues))
        
        # Fetch discussions if requested
        if template.include_discussions:
            self.logger.info(f"FETCHING DISCUSSIONS", repo=repo.full_name)
            discussions = await self.fetch_discussions_async(repo)
            self.logger.info(f"DISCUSSIONS FETCHED", repo=repo.full_name, count=len(discussions))
            repo_issues.extend(discussions)
        
        # Filter by conditions
        self.logger.info("APPLYING CONDITIONS FILTER",
                        repo=repo.full_name,
                        total_issues=len(repo_issues),
                        conditions_count=len(template.conditions),
                        condition_logic=template.condition_logic)
        
        # Log the actual conditions being used
        for i, condition in enumerate(template.conditions):
            self.logger.info("CONDITION DETAILS",
                           repo=repo.full_name,
                           condition_index=i,
                           condition_type=condition.type.value if hasattr(condition.type, 'value') else str(condition.type),
                           condition_value=condition.value,
                           case_sensitive=getattr(condition, 'case_sensitive', True),
                           negate=getattr(condition, 'negate', False))
        
        try:
            matching_issues = []
            sample_checks = []  # Track first few for debugging
            
            for i, issue in enumerate(repo_issues):
                try:
                    matches = issue.matches_conditions(template.conditions, template.condition_logic)
                    
                    # Log details for first few issues
                    if i < 5:  # First 5 issues per repo
                        sample_checks.append({
                            'issue_number': issue.number,
                            'issue_title': issue.title[:50] + '...' if len(issue.title) > 50 else issue.title,
                            'labels': [label.name for label in issue.labels],
                            'matches': matches
                        })
                    
                    if matches:
                        matching_issues.append(issue)
                        # Log all matches for debugging
                        self.logger.info("ISSUE MATCHED CONDITIONS",
                                       repo=repo.full_name,
                                       issue_number=issue.number,
                                       issue_title=issue.title[:50])
                except Exception as e:
                    self.logger.error("ERROR FILTERING INDIVIDUAL ISSUE",
                                    repo=repo.full_name,
                                    issue_number=issue.number,
                                    issue_title=issue.title[:50],
                                    error=str(e))
                    continue
            
            # Log sample check results
            self.logger.info("SAMPLE FILTERING RESULTS",
                           repo=repo.full_name,
                           sample_checks=sample_checks)
            
            self.logger.info("CONDITION FILTERING COMPLETE", 
                            repo=repo.full_name,
                            matching_issues=len(matching_issues),
                            filtered_out=len(repo_issues) - len(matching_issues))
            
            return matching_issues
            
        except Exception as e:
            self.logger.error("Critical error during condition filtering",
                            repo=repo.full_name,
                            error=str(e))
            return []

    async def fetch_all_issues_async(self, template: QueryTemplate, progress: Progress | None = None, force_refresh: bool = False) -> list[GitHubIssue]:
        """Fetch all issues matching the template criteria using parallel requests.
        
        Args:
            template: Query template with repositories and conditions
            progress: Optional progress bar
            force_refresh: Force refresh from API, ignore cache
            
        Returns:
            List of matching GitHub issues
        """
        # Check disk cache first (unless force refresh)
        if self.disk_cache and not force_refresh:
            self.logger.info("Checking disk cache", template_name=template.name)
            cached_issues = self.disk_cache.get_cached_issues(template)
            if cached_issues is not None:
                self.logger.info("Cache hit - returning cached issues", 
                               template_name=template.name,
                               cached_count=len(cached_issues))
                console.print(f"[green]Loaded {len(cached_issues)} issues from cache[/green]")
                
                # Apply ignore list and custom fields to cached issues
                for issue in cached_issues:
                    if issue.number in template.ignored_issues:
                        issue.is_ignored = True
                    
                    # Apply custom status and notes
                    if issue.number in template.status_overrides:
                        status_value = template.status_overrides[issue.number]
                        # Ensure we have an IssueStatus enum (convert from string if needed)
                        if isinstance(status_value, str):
                            issue.custom_status = IssueStatus(status_value)
                        else:
                            issue.custom_status = status_value
                    else:
                        # If no custom status is set and the issue is closed, automatically set to done
                        if issue.state == "closed" and issue.custom_status == IssueStatus.NONE:
                            issue.custom_status = IssueStatus.DONE
                    
                    if issue.number in template.notes:
                        issue.custom_note = template.notes[issue.number]
                
                # Sort cached issues by: Type → Repo → Date (newest first) → Title
                cached_issues.sort(key=lambda x: (
                    x.detected_type.value,
                    x.repository_name,
                    -x.updated_at.timestamp(),  # Negative for descending order
                    x.title.lower()
                ))
                
                return cached_issues
            else:
                self.logger.info("Cache miss - will fetch from API", template_name=template.name)
        elif force_refresh:
            self.logger.info("Force refresh requested - ignoring cache", template_name=template.name)
            if self.disk_cache:
                # Clear this template's cache entry when force refreshing
                self.disk_cache.clear_cache(template)
                self.logger.info("Cleared cache for template", template_name=template.name)
        
        all_issues: list[GitHubIssue] = []
        
        # Fetch repositories sequentially
        if progress:
            for i, repo in enumerate(template.repositories):
                self.logger.info(f"STARTING REPO {i+1}/{len(template.repositories)}", 
                               repo=repo.full_name,
                               index=i)
                task_id = progress.add_task(f"[cyan]{repo.full_name}", total=1)
                try:
                    repo_issues = await self.fetch_repo_data_async(repo, template, task_id)
                    self.logger.info(f"REPO COMPLETE {i+1}/{len(template.repositories)}", 
                                   repo=repo.full_name,
                                   issues_found=len(repo_issues))
                    all_issues.extend(repo_issues)
                    progress.update(task_id, completed=1)
                except Exception as e:
                    console.print(f"[red]Error fetching from {repo.full_name}: {e}[/red]")
                    self.logger.error("Error fetching repository", 
                                    repo=repo.full_name,
                                    error=str(e))
        else:
            for i, repo in enumerate(template.repositories):
                self.logger.info(f"STARTING REPO {i+1}/{len(template.repositories)}", 
                               repo=repo.full_name,
                               index=i)
                try:
                    repo_issues = await self.fetch_repo_data_async(repo, template, None)
                    self.logger.info(f"REPO COMPLETE {i+1}/{len(template.repositories)}", 
                                   repo=repo.full_name,
                                   issues_found=len(repo_issues))
                    all_issues.extend(repo_issues)
                except Exception as e:
                    console.print(f"[red]Error fetching from {repo.full_name}: {e}[/red]")
                    self.logger.error("Error fetching repository", 
                                    repo=repo.full_name,
                                    error=str(e))
        
        # Apply ignore list and custom fields
        for issue in all_issues:
            if issue.number in template.ignored_issues:
                issue.is_ignored = True
            
            # Apply custom status and notes
            if issue.number in template.status_overrides:
                status_value = template.status_overrides[issue.number]
                # Ensure we have an IssueStatus enum (convert from string if needed)
                if isinstance(status_value, str):
                    issue.custom_status = IssueStatus(status_value)
                else:
                    issue.custom_status = status_value
            else:
                # If no custom status is set and the issue is closed, automatically set to done
                if issue.state == "closed" and issue.custom_status == IssueStatus.NONE:
                    issue.custom_status = IssueStatus.DONE
            
            if issue.number in template.notes:
                issue.custom_note = template.notes[issue.number]
        
        # Sort by: Type → Repo → Date (newest first) → Title
        all_issues.sort(key=lambda x: (
            x.detected_type.value,
            x.repository_name,
            -x.updated_at.timestamp(),  # Negative for descending order
            x.title.lower()
        ))
        
        # Log final results
        self.logger.info("FETCH ALL ISSUES COMPLETE", 
                        total_repos=len(template.repositories),
                        total_issues_found=len(all_issues),
                        repos_processed=[r.full_name for r in template.repositories])
        
        # Cache results to disk (only if we got results)
        if self.disk_cache and all_issues:
            self.disk_cache.cache_issues(template, all_issues)
        
        return all_issues

    async def fetch_all_issues_with_progress(self, template: QueryTemplate, force_refresh: bool = False) -> list[GitHubIssue]:
        """Fetch all issues with progress bar."""
        # For now, skip the Rich progress bar in Textual context
        # as it doesn't display well
        return await self.fetch_all_issues_async(template, None, force_refresh)