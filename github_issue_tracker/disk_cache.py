"""Disk-based caching for GitHub issues."""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .models import GitHubIssue, QueryTemplate


class DiskCache:
    """Disk-based cache for GitHub issues."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize disk cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_key(self, template: QueryTemplate) -> str:
        """Generate cache key from template."""
        # Create hash from template excluding dynamic fields
        cache_data = {
            "repositories": [repo.model_dump() for repo in template.repositories],
            "conditions": [cond.model_dump() for cond in template.conditions],
            "condition_logic": template.condition_logic,
            "state": template.state,
            "include_discussions": template.include_discussions,
            "max_age_months": template.max_age_months
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get cache metadata file path."""
        return self.cache_dir / f"{cache_key}.meta.json"
    
    def get_cached_issues(self, template: QueryTemplate) -> list[GitHubIssue] | None:
        """Get cached issues for template."""
        cache_key = self._get_cache_key(template)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)
        
        if not cache_path.exists() or not meta_path.exists():
            return None
            
        # Check if cache is still valid
        try:
            with open(meta_path) as f:
                metadata = json.load(f)
            
            cached_time = datetime.fromisoformat(metadata["cached_at"])
            # Cache valid for 24 hours by default
            cache_ttl = timedelta(hours=24)
            
            if datetime.now() - cached_time > cache_ttl:
                return None
                
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
            
        # Load cached issues
        try:
            with open(cache_path) as f:
                issues_data = json.load(f)
            
            issues = []
            for issue_data in issues_data:
                # Convert datetime strings back to datetime objects
                for date_field in ["created_at", "updated_at", "closed_at"]:
                    if issue_data.get(date_field):
                        issue_data[date_field] = datetime.fromisoformat(issue_data[date_field])
                
                issue = GitHubIssue(**issue_data)
                issues.append(issue)
                
            return issues
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def cache_issues(self, template: QueryTemplate, issues: list[GitHubIssue]) -> None:
        """Cache issues to disk."""
        # Don't cache empty results
        if not issues:
            return
            
        cache_key = self._get_cache_key(template)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)
        
        # Convert issues to JSON-serializable format
        issues_data = []
        for issue in issues:
            issue_dict = issue.model_dump()
            # Convert datetime objects to ISO strings
            for date_field in ["created_at", "updated_at", "closed_at"]:
                if issue_dict.get(date_field):
                    issue_dict[date_field] = issue_dict[date_field].isoformat()
            issues_data.append(issue_dict)
        
        # Save issues data
        with open(cache_path, "w") as f:
            json.dump(issues_data, f, indent=2)
        
        # Save metadata
        metadata = {
            "cached_at": datetime.now().isoformat(),
            "template_name": template.name,
            "issue_count": len(issues),
            "repositories": [repo.full_name for repo in template.repositories]
        }
        
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def clear_cache(self, template: QueryTemplate | None = None) -> None:
        """Clear cache files."""
        if template:
            # Clear specific template cache
            cache_key = self._get_cache_key(template)
            cache_path = self._get_cache_path(cache_key)
            meta_path = self._get_metadata_path(cache_key)
            
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def get_cache_info(self) -> dict[str, Any]:
        """Get information about cached data."""
        cache_info = {
            "cache_dir": str(self.cache_dir),
            "total_files": len(list(self.cache_dir.glob("*.json"))),
            "cached_templates": []
        }
        
        for meta_file in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_file) as f:
                    metadata = json.load(f)
                cache_info["cached_templates"].append({
                    "name": metadata.get("template_name", "Unknown"),
                    "cached_at": metadata.get("cached_at"),
                    "issue_count": metadata.get("issue_count", 0),
                    "repositories": metadata.get("repositories", [])
                })
            except (json.JSONDecodeError, KeyError):
                continue
        
        return cache_info