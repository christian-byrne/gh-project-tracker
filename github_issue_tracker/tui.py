"""Terminal User Interface for GitHub Issue Tracker."""

import re
import time
import webbrowser
from pathlib import Path
from typing import Any

import yaml
from fuzzywuzzy import fuzz
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Static,
    TextArea,
)

from .filter_config import FilterConfigModal
from .github_client import GitHubClient
from .models import GitHubIssue, IssueStatus, IssueType, QueryTemplate
from enum import Enum
from .simple_logger import log


class SortColumn(Enum):
    """Available columns for sorting."""
    STATUS = "status"
    TYPE = "type"
    NUMBER = "number"
    REPO = "repo"
    TITLE = "title"
    UPDATED = "updated"


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters except spaces
    text = re.sub(r'[^\w\s]', '', text)
    return text


def fuzzy_match(query: str, target: str, threshold: int = 70) -> bool:
    """Check if query fuzzy matches target text."""
    if not query or not target:
        return False
    
    # Normalize both strings
    norm_query = normalize_text(query)
    norm_target = normalize_text(target)
    
    # Direct substring match (highest priority)
    if norm_query in norm_target:
        return True
    
    # Fuzzy ratio match
    ratio = fuzz.partial_ratio(norm_query, norm_target)
    return ratio >= threshold


class FilterModal(ModalScreen):
    """Modal for entering filter text."""

    def __init__(self, current_filter: str = ""):
        """Initialize filter modal."""
        super().__init__()
        self.current_filter = current_filter

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        yield Container(
            Label("Filter Issues"),
            Input(
                value=self.current_filter,
                placeholder="Enter filter text...",
                id="filter-input"
            ),
            Horizontal(
                Button("Apply", variant="primary", id="apply-filter"),
                Button("Clear", variant="warning", id="clear-filter"),
                Button("Cancel", variant="default", id="cancel-filter"),
                classes="button-row",
            ),
            id="filter-modal",
        )

    @on(Button.Pressed, "#apply-filter")
    def apply_filter(self) -> None:
        """Apply the filter and close modal."""
        filter_input = self.query_one("#filter-input", Input)
        self.dismiss(filter_input.value)

    @on(Button.Pressed, "#clear-filter")
    def clear_filter(self) -> None:
        """Clear filter and close modal."""
        self.dismiss("")

    @on(Button.Pressed, "#cancel-filter")
    def cancel_filter(self) -> None:
        """Cancel and close modal."""
        self.dismiss(None)


class NoteModal(ModalScreen):
    """Modal for editing issue notes."""

    def __init__(self, issue: GitHubIssue):
        """Initialize note modal."""
        super().__init__()
        self.issue = issue

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        yield Container(
            Label(f"Edit Note for Issue #{self.issue.number}"),
            TextArea(self.issue.custom_note, id="note-input"),
            Horizontal(
                Button("Save", variant="primary", id="save-note"),
                Button("Cancel", variant="default", id="cancel-note"),
                classes="button-row",
            ),
            id="note-modal",
        )

    @on(Button.Pressed, "#save-note")
    def save_note(self) -> None:
        """Save the note and close modal."""
        note_input = self.query_one("#note-input", TextArea)
        self.dismiss(note_input.text)

    @on(Button.Pressed, "#cancel-note")
    def cancel_note(self) -> None:
        """Cancel and close modal."""
        self.dismiss(None)


class IssueTrackerApp(App):
    """Main TUI application for tracking GitHub issues."""

    CSS = """
    #issue-table {
        height: 1fr;
    }
    
    #stats {
        height: 3;
        padding: 0 1;
        background: $surface;
        border: solid $primary;
    }
    
    #loading-container {
        align: center middle;
        height: 100%;
    }
    
    LoadingIndicator {
        height: 5;
    }
    
    .hidden {
        display: none;
    }
    
    #note-modal, #filter-modal {
        width: 60;
        height: 20;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }
    
    #filter-modal {
        height: 12;
    }
    
    #filter-input {
        margin: 1 0;
    }
    
    #note-input {
        height: 10;
        margin: 1 0;
    }
    
    .button-row {
        height: 3;
        align: center middle;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_cached", "Refresh (use cache)"),
        Binding("R", "refresh_force", "Force Refresh (ignore cache)"),
        Binding("o", "open_issue", "Open in Browser"),
        Binding("i", "toggle_ignore", "Ignore/Unignore"),
        Binding("n", "edit_note", "Edit Note"),
        Binding("s", "cycle_status", "Cycle Status"),
        Binding("f", "filter", "Filter Text"),
        Binding("c", "configure", "Configure Filters"),
        Binding("w", "save", "Save Changes"),
        Binding("h", "toggle_hidden", "Toggle Hidden"),
        Binding("t", "cycle_sort", "Cycle Sort"),
    ]

    def __init__(self, template_path: str):
        """Initialize the app with a template."""
        super().__init__()
        self.template_path = Path(template_path)
        self.template: QueryTemplate | None = None
        self.issues: list[GitHubIssue] = []
        self.filtered_issues: list[GitHubIssue] = []
        self.show_hidden = False
        self.filter_text = ""
        self.is_loading = True
        self.current_sort = SortColumn.UPDATED  # Default sort by updated date
        self.sort_reverse = True  # Default to newest first

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield Container(
            Container(
                LoadingIndicator(),
                Label("Initializing GitHub Issue Tracker..."),
                id="loading-container"
            ),
            Container(
                Static("", id="stats"),
                DataTable(id="issue-table"),
                id="main-container",
                classes="hidden"
            )
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app on mount."""
        log("=== App on_mount started ===")
        
        # Update loading message
        loading_label = self.query_one("#loading-container Label", Label)
        loading_label.update("Loading template...")
        
        await self.load_template()
        log(f"Template loaded: {self.template.name if self.template else 'None'}")
        
        self.setup_table()
        
        # Update loading message for fetching
        loading_label.update(f"Fetching issues from {len(self.template.repositories)} repositories...")
        
        # Load from cache if available, otherwise fetch fresh
        log("Starting initial refresh (will use cache if available)...")
        await self.refresh_issues(force_refresh=False)
        
        # Hide loading and show main content
        self.query_one("#loading-container").add_class("hidden")
        self.query_one("#main-container").remove_class("hidden")
        self.is_loading = False
        
        log(f"After initial fetch: {len(self.issues)} issues, {len(self.filtered_issues)} filtered")
        
        self.update_display()
        log("=== App on_mount completed ===")

    async def load_template(self) -> None:
        """Load the query template from YAML file."""
        with open(self.template_path) as f:
            data = yaml.safe_load(f)
        self.template = QueryTemplate(**data)
        self.title = f"GitHub Issue Tracker - {self.template.name}"

    def setup_table(self) -> None:
        """Set up the data table columns."""
        table = self.query_one("#issue-table", DataTable)
        table.add_columns(
            "Status",
            "Type",
            "#",
            "Repo",
            "Title",
            "Note",
            "Labels",
            "Updated",
        )
        table.cursor_type = "row"

    async def refresh_issues(self, force_refresh: bool = False) -> None:
        """Fetch issues from GitHub."""
        log(f"refresh_issues called with force_refresh={force_refresh}")
        if not self.template:
            log("ERROR: No template!")
            return

        try:
            # Show fetching status
            if force_refresh:
                self.query_one("#stats", Static).update(
                    f"[yellow bold]FORCE REFRESHING from API (ignoring cache)... Please wait...[/yellow bold]"
                )
            else:
                self.query_one("#stats", Static).update(
                    f"[cyan]Refreshing issues from {len(self.template.repositories)} repositories (using cache if available)...[/cyan]"
                )
            
            # Force UI update
            self.refresh()
            
            log(f"About to fetch issues from {len(self.template.repositories)} repos")
            start_time = time.time()
            async with GitHubClient() as client:
                self.issues = await client.fetch_all_issues_with_progress(self.template, force_refresh)
            
            elapsed = time.time() - start_time
            log(f"Fetch complete. Got {len(self.issues)} issues in {elapsed:.1f}s")
            
            source = "fresh API data" if force_refresh else "cache/API"
            
            if self.issues:
                self.query_one("#stats", Static).update(
                    f"[green]Loaded {len(self.issues)} issues from {source} in {elapsed:.1f}s[/green]"
                )
            else:
                # If no issues, it might be rate limited or no results
                self.query_one("#stats", Static).update(
                    f"[yellow]No issues found after filtering. Fetched from {len(self.template.repositories)} repos. Check conditions or logs.[/yellow]"
                )
            
            self.apply_filter()
            log(f"After apply_filter, filtered_issues={len(self.filtered_issues)}")
        except Exception as e:
            # Show error in the stats bar
            log(f"EXCEPTION in refresh_issues: {type(e).__name__}: {e}")
            import traceback
            log(traceback.format_exc())
            
            error_msg = str(e)
            if "403" in error_msg or "rate limit" in error_msg.lower():
                self.query_one("#stats", Static).update(
                    f"[red]GitHub API rate limit exceeded. Make sure you're authenticated with 'gh auth login'[/red]"
                )
            else:
                # Escape error message to prevent markup issues
                error_msg_escaped = str(e).replace("[", "\\[").replace("]", "\\]")
                self.query_one("#stats", Static).update(f"[red]Error fetching issues: {error_msg_escaped}[/red]")
            self.issues = []
            self.filtered_issues = []

    def apply_filter(self) -> None:
        """Apply current filter to issues with fuzzy matching."""
        filtered = self.issues if self.show_hidden else [i for i in self.issues if not i.is_ignored]
        
        if self.filter_text:
            query = self.filter_text.strip()
            filtered = [
                i for i in filtered
                if self._matches_search_query(i, query)
            ]
        
        # Apply sorting
        self.filtered_issues = self._sort_issues(filtered)
    
    def _matches_search_query(self, issue: GitHubIssue, query: str) -> bool:
        """Check if issue matches search query using fuzzy matching."""
        # Exact number match (highest priority)
        if query.isdigit() and str(issue.number) == query:
            return True
        
        # Fuzzy match against title (most important)
        if fuzzy_match(query, issue.title, threshold=60):
            return True
        
        # Fuzzy match against repository name
        if fuzzy_match(query, issue.repository_name, threshold=70):
            return True
        
        # Fuzzy match against labels
        for label in issue.labels:
            if fuzzy_match(query, label.name, threshold=75):
                return True
        
        # Fuzzy match against body (if available, lower threshold)
        if issue.body and fuzzy_match(query, issue.body, threshold=50):
            return True
        
        # Fuzzy match against author name
        if fuzzy_match(query, issue.user.login, threshold=80):
            return True
        
        return False

    def _sort_issues(self, issues: list[GitHubIssue]) -> list[GitHubIssue]:
        """Sort issues based on current sort column."""
        if self.current_sort == SortColumn.STATUS:
            key_func = lambda x: (x.custom_status.value, x.updated_at)
        elif self.current_sort == SortColumn.TYPE:
            key_func = lambda x: (x.detected_type.value, x.updated_at)
        elif self.current_sort == SortColumn.NUMBER:
            key_func = lambda x: x.number
        elif self.current_sort == SortColumn.REPO:
            key_func = lambda x: (x.repository_name, x.updated_at)
        elif self.current_sort == SortColumn.TITLE:
            key_func = lambda x: x.title.lower()
        elif self.current_sort == SortColumn.UPDATED:
            key_func = lambda x: x.updated_at
        else:
            key_func = lambda x: x.updated_at
        
        return sorted(issues, key=key_func, reverse=self.sort_reverse)

    def update_display(self) -> None:
        """Update the display with current issues."""
        table = self.query_one("#issue-table", DataTable)
        
        # Save current cursor position
        current_row = table.cursor_coordinate.row if table.cursor_coordinate else 0
        
        table.clear()
        
        for issue in self.filtered_issues:
            status_text = self._get_status_display(issue)
            type_text = self._get_type_display(issue)
            
            # Truncate title to 80 characters
            truncated_title = issue.title[:80] + "..." if len(issue.title) > 80 else issue.title
            title_text = Text(truncated_title)
            
            # Style based on status
            if issue.custom_status == IssueStatus.FUTURE:
                title_text.stylize("dim")
            elif issue.custom_status == IssueStatus.DONE:
                title_text.stylize("dim italic")
            
            if issue.is_ignored:
                title_text.stylize("dim strike")
            
            # Add state indicator for closed issues
            if issue.state == "closed":
                title_text = Text("✓ ", style="green") + title_text
                
            labels = ", ".join(issue.label_names)
            updated = issue.updated_at.strftime("%Y-%m-%d")
            
            # Format note text
            note_text = Text(issue.custom_note[:30] + "..." if issue.custom_note and len(issue.custom_note) > 30 else issue.custom_note or "")
            if issue.custom_note:
                note_text.stylize("italic cyan")
            
            table.add_row(
                status_text,
                type_text,
                str(issue.number),
                issue.repository_name,
                title_text,
                note_text,
                labels,
                updated,
                key=str(issue.id),
            )
        
        # Update stats
        total = len(self.issues)
        shown = len(self.filtered_issues)
        ignored = sum(1 for i in self.issues if i.is_ignored)
        
        # Get sort display
        sort_display = f"{self.current_sort.value.title()} {'↓' if self.sort_reverse else '↑'}"
        
        stats_text = (
            f"Total: {total} | Shown: {shown} | Ignored: {ignored} | "
            f"Filter: {self.filter_text or 'none'} | "
            f"Hidden: {'shown' if self.show_hidden else 'hidden'} | "
            f"Sort: {sort_display}"
        )
        self.query_one("#stats", Static).update(stats_text)
        
        # Restore cursor position if possible
        if shown > 0 and current_row < shown:
            table.cursor_coordinate = (current_row, 0)

    def _get_status_display(self, issue: GitHubIssue) -> Text:
        """Get formatted status display for an issue."""
        status_map = {
            IssueStatus.NONE: ("", "white"),
            IssueStatus.IN_PROGRESS: ("🔄 Progress", "yellow"),
            IssueStatus.BLOCKED: ("🚫 Blocked", "red"),
            IssueStatus.FUTURE: ("📅 Future", "dim blue"),
            IssueStatus.INVESTIGATING: ("🔍 Investigating", "cyan"),
            IssueStatus.READY: ("✅ Ready", "green"),
            IssueStatus.WAITING: ("⏳ Waiting", "magenta"),
            IssueStatus.DONE: ("✔️  Done", "dim green"),
            IssueStatus.HELP_WANTED_OS: ("🆘 Help: OS", "bright_yellow"),
            IssueStatus.HELP_WANTED_TEAM: ("🆘 Help: Team", "bright_magenta"),
        }
        
        text, color = status_map[issue.custom_status]
        return Text(text, style=color)

    def _get_type_display(self, issue: GitHubIssue) -> Text:
        """Get formatted type display for an issue."""
        type_map = {
            IssueType.BUG: ("🐛 Bug", "red"),
            IssueType.FEATURE: ("✨ Feature", "cyan"),
            IssueType.QUESTION: ("❓ Question", "yellow"),
            IssueType.DISCUSSION: ("💬 Discuss", "magenta"),
            IssueType.ISSUE: ("📋 Issue", "white"),
        }
        
        text, color = type_map[issue.detected_type]
        return Text(text, style=color)

    def get_current_issue(self) -> GitHubIssue | None:
        """Get the currently selected issue."""
        table = self.query_one("#issue-table", DataTable)
        if table.row_count == 0:
            return None
        
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if row_key is None or row_key.value is None:
            return None
        issue_id = int(row_key.value)
        
        for issue in self.filtered_issues:
            if issue.id == issue_id:
                return issue
        return None

    async def action_refresh_cached(self) -> None:
        """Refresh issues from GitHub (use cache if available)."""
        await self.refresh_issues(force_refresh=False)
        self.update_display()
    
    async def action_refresh_force(self) -> None:
        """Force refresh issues from GitHub (ignore cache)."""
        log("action_refresh_force called!")
        self.notify("Force refresh triggered!")
        await self.refresh_issues(force_refresh=True)
        self.update_display()

    def action_open_issue(self) -> None:
        """Open current issue in browser."""
        issue = self.get_current_issue()
        if issue:
            import subprocess
            import sys
            
            url = issue.html_url
            log(f"Opening issue URL: {url}")
            
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", url], check=True)
                elif sys.platform == "win32":  # Windows
                    subprocess.run(["start", url], shell=True, check=True)
                else:  # Linux/Unix
                    # Try xdg-open first, fall back to webbrowser
                    try:
                        subprocess.run(["xdg-open", url], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        log("xdg-open failed, trying webbrowser module")
                        webbrowser.open(url)
                
                self.notify(f"Opened issue #{issue.number}")
            except Exception as e:
                log(f"Failed to open URL: {e}")
                self.notify(f"Failed to open issue: {e}", severity="error")

    def action_toggle_ignore(self) -> None:
        """Toggle ignore status of current issue."""
        issue = self.get_current_issue()
        if not issue or not self.template:
            return
        
        issue.is_ignored = not issue.is_ignored
        
        if issue.is_ignored:
            if issue.number not in self.template.ignored_issues:
                self.template.ignored_issues.append(issue.number)
        else:
            if issue.number in self.template.ignored_issues:
                self.template.ignored_issues.remove(issue.number)
        
        self.apply_filter()
        self.update_display()
        self._auto_save()

    def action_cycle_status(self) -> None:
        """Cycle through status options for current issue."""
        issue = self.get_current_issue()
        if not issue or not self.template:
            return
        
        statuses = list(IssueStatus)
        current_idx = statuses.index(issue.custom_status)
        next_idx = (current_idx + 1) % len(statuses)
        issue.custom_status = statuses[next_idx]
        
        if issue.custom_status == IssueStatus.NONE:
            self.template.status_overrides.pop(issue.number, None)
        else:
            # Store the string value, not the enum object
            self.template.status_overrides[issue.number] = issue.custom_status.value
        
        self.update_display()
        self._auto_save()

    async def action_edit_note(self) -> None:
        """Edit note for current issue."""
        issue = self.get_current_issue()
        if not issue or not self.template:
            return
        
        self._current_issue_for_note = issue
        self.push_screen(NoteModal(issue), callback=self._handle_note_result)
    
    def _handle_note_result(self, result: str | None) -> None:
        """Handle note modal result."""
        if result is not None and hasattr(self, '_current_issue_for_note'):
            issue = self._current_issue_for_note
            issue.custom_note = result
            if result:
                self.template.notes[issue.number] = result
            else:
                self.template.notes.pop(issue.number, None)
            
            self.update_display()
            self._auto_save()
            delattr(self, '_current_issue_for_note')

    async def action_filter(self) -> None:
        """Prompt for filter text."""
        self.push_screen(FilterModal(self.filter_text), callback=self._handle_filter_result)
    
    def _handle_filter_result(self, result: str | None) -> None:
        """Handle filter modal result."""
        if result is not None:
            self.filter_text = result
            self.apply_filter()
            self.update_display()

    def _auto_save(self) -> None:
        """Auto-save current state to YAML file."""
        if not self.template:
            return
        
        try:
            # Convert template to dict for YAML serialization
            data = self.template.model_dump()
            
            # Convert all enum values to strings to avoid Python-specific tags
            if "status_overrides" in data and data["status_overrides"]:
                data["status_overrides"] = {
                    k: v.value if hasattr(v, 'value') else str(v)
                    for k, v in data["status_overrides"].items()
                }
            
            # Convert condition types to strings
            if "conditions" in data and data["conditions"]:
                for condition in data["conditions"]:
                    if "type" in condition and hasattr(condition["type"], "value"):
                        condition["type"] = condition["type"].value
            
            # Save to file with safe dump to avoid Python-specific tags
            with open(self.template_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            
            log("Auto-saved changes")
        except Exception as e:
            log(f"Failed to auto-save: {e}")
            self.notify(f"Failed to auto-save: {e}", severity="error")
    
    def action_save(self) -> None:
        """Manually save current state (kept for compatibility)."""
        self._auto_save()
        self.notify("Changes saved!")

    def action_toggle_hidden(self) -> None:
        """Toggle showing hidden/ignored issues."""
        self.show_hidden = not self.show_hidden
        self.apply_filter()
        self.update_display()

    def action_cycle_sort(self) -> None:
        """Cycle through sort columns."""
        # Get list of sort columns
        sort_columns = list(SortColumn)
        current_idx = sort_columns.index(self.current_sort)
        
        # Move to next column
        next_idx = (current_idx + 1) % len(sort_columns)
        self.current_sort = sort_columns[next_idx]
        
        # Default sort directions for each column
        if self.current_sort in [SortColumn.UPDATED, SortColumn.NUMBER]:
            self.sort_reverse = True  # Newest/highest first
        else:
            self.sort_reverse = False  # Alphabetical
        
        self.apply_filter()
        self.update_display()

    async def action_configure(self) -> None:
        """Open filter configuration modal."""
        if not self.template:
            return
            
        # Use push_screen instead of push_screen_wait to avoid worker issues
        self.push_screen(FilterConfigModal(self.template), callback=self._handle_filter_config)
    
    async def _handle_filter_config(self, result: tuple[str, Any] | None) -> None:
        """Handle filter configuration result."""
        if result is None:
            return
            
        action, data = result
        
        if action == "apply":
            # Apply temporary filter changes
            self.template.state = data["state"]
            self.template.include_discussions = data["include_discussions"]
            await self.refresh_issues()
            self.update_display()
            
        elif action == "save_as":
            # Save as new template
            from pathlib import Path

            import yaml
            
            new_template = data
            template_dir = Path("templates")
            template_dir.mkdir(exist_ok=True)
            
            # Generate filename from name
            filename = new_template.name.lower().replace(" ", "-") + ".yaml"
            filepath = template_dir / filename
            
            # Save the new template
            with open(filepath, "w") as f:
                yaml.dump(new_template.model_dump(), f, default_flow_style=False, sort_keys=False)
            
            self.notify(f"Saved new template: {filepath}")