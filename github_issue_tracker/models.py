"""Data models for GitHub Issue Tracker."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConditionType(str, Enum):
    """Types of conditions for filtering issues."""

    LABEL = "label"
    TITLE_CONTAINS = "title_contains"
    BODY_CONTAINS = "body_contains"
    AUTHOR = "author"
    ASSIGNEE = "assignee"
    MILESTONE = "milestone"
    CREATED_AFTER = "created_after"
    UPDATED_AFTER = "updated_after"


class IssueStatus(str, Enum):
    """Custom status for tracking issues."""

    NONE = "none"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FUTURE = "future"
    INVESTIGATING = "investigating"
    READY = "ready"
    WAITING = "waiting"
    DONE = "done"
    HELP_WANTED_OS = "help_wanted_os"
    HELP_WANTED_TEAM = "help_wanted_team"


class IssueType(str, Enum):
    """Types of GitHub items."""

    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    DISCUSSION = "discussion"
    ISSUE = "issue"  # generic issue


class Repository(BaseModel):
    """GitHub repository reference."""

    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        """Get full repository name."""
        return f"{self.owner}/{self.repo}"


class Condition(BaseModel):
    """Search condition for filtering issues."""

    type: ConditionType
    value: str
    case_sensitive: bool = True
    negate: bool = False


class QueryTemplate(BaseModel):
    """YAML template for GitHub issue queries."""

    name: str
    description: str = ""
    repositories: list[Repository]
    conditions: list[Condition]
    condition_logic: str = "and"  # "and" or "or" - how to combine conditions
    state: str = "open"  # open, closed, all
    include_discussions: bool = False
    max_age_months: int = 12  # Only fetch issues updated in last N months
    ignored_issues: list[int] = Field(default_factory=list)
    notes: dict[int, str] = Field(default_factory=dict)
    status_overrides: dict[int, IssueStatus] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        use_enum_values = True


class GitHubUser(BaseModel):
    """GitHub user information."""

    login: str
    id: int | str  # Allow both integer and string IDs (GraphQL vs REST API)
    avatar_url: str
    html_url: str


class GitHubLabel(BaseModel):
    """GitHub label information."""

    id: int
    name: str
    color: str
    description: str | None = None


class GitHubIssue(BaseModel):
    """GitHub issue information."""

    id: int
    number: int
    title: str
    body: str | None
    state: str
    html_url: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    user: GitHubUser
    assignee: GitHubUser | None = None
    assignees: list[GitHubUser] = Field(default_factory=list)
    labels: list[GitHubLabel] = Field(default_factory=list)
    repository_url: str
    comments: int = 0
    
    # Custom fields for tracking
    repository_name: str = ""
    custom_status: IssueStatus = IssueStatus.NONE
    custom_note: str = ""
    is_ignored: bool = False
    is_discussion: bool = False
    
    @property
    def detected_type(self) -> IssueType:
        """Detect the type of issue based on labels and title."""
        # Check labels first
        label_names_lower = [label.name.lower() for label in self.labels]
        
        if "bug" in label_names_lower:
            return IssueType.BUG
        if any(feat in label_names_lower for feat in ["feature", "enhancement", "feature request"]):
            return IssueType.FEATURE
        if "question" in label_names_lower:
            return IssueType.QUESTION
        
        # Check title for [type] pattern
        title_lower = self.title.lower()
        if "[bug]" in title_lower:
            return IssueType.BUG
        if "[feature]" in title_lower or "[feat]" in title_lower:
            return IssueType.FEATURE
        if "[question]" in title_lower:
            return IssueType.QUESTION
        
        # Check if it's a discussion
        if self.is_discussion:
            return IssueType.DISCUSSION
            
        return IssueType.ISSUE

    @property
    def label_names(self) -> list[str]:
        """Get list of label names."""
        return [label.name for label in self.labels]

    def matches_conditions(self, conditions: list[Condition], logic: str = "and") -> bool:
        """Check if issue matches conditions using specified logic."""
        if not conditions:
            return True
            
        if logic == "or":
            # OR logic: any condition can match
            for condition in conditions:
                match = self._check_condition(condition)
                if condition.negate:
                    match = not match
                if match:
                    return True
            return False
        else:
            # AND logic: all conditions must match (default)
            for condition in conditions:
                match = self._check_condition(condition)
                if condition.negate:
                    match = not match
                if not match:
                    return False
            return True

    def _check_condition(self, condition: Condition) -> bool:
        """Check if issue matches a single condition."""
        if condition.type == ConditionType.LABEL:
            return condition.value in self.label_names
        elif condition.type == ConditionType.TITLE_CONTAINS:
            title = self.title.lower() if not condition.case_sensitive else self.title
            value = condition.value.lower() if not condition.case_sensitive else condition.value
            return value in title
        elif condition.type == ConditionType.BODY_CONTAINS:
            if not self.body:
                return False
            body = self.body.lower() if not condition.case_sensitive else self.body
            value = condition.value.lower() if not condition.case_sensitive else condition.value
            return value in body
        elif condition.type == ConditionType.AUTHOR:
            return self.user.login == condition.value
        elif condition.type == ConditionType.ASSIGNEE:
            if not self.assignee:
                return False
            return self.assignee.login == condition.value
        elif condition.type == ConditionType.CREATED_AFTER:
            created_date = datetime.fromisoformat(condition.value)
            return self.created_at >= created_date
        elif condition.type == ConditionType.UPDATED_AFTER:
            updated_date = datetime.fromisoformat(condition.value)
            return self.updated_at >= updated_date
        return False