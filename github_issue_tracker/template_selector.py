"""Template selection screen for GitHub Issue Tracker."""

import json
from datetime import datetime
from pathlib import Path

import yaml
from rich.console import Console
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Static

console = Console()


class TemplateSelectorApp(App):
    """Application for selecting issue tracking templates."""

    CSS = """
    #template-table {
        height: 1fr;
    }
    
    #info {
        height: 3;
        padding: 0 1;
        background: $surface;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select", show=True),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        """Initialize the template selector."""
        super().__init__()
        self.templates = []
        self.usage_file = Path.home() / ".config" / "gh-tracker" / "usage.json"
        self.usage_data = {}

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield Container(
            Static("Select a template to track issues", id="info"),
            DataTable(id="template-table"),
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.title = "GitHub Issue Tracker - Template Selection"
        self.load_usage_data()
        self.setup_table()
        self.load_templates()
        self.update_display()
        # Focus the table
        table = self.query_one("#template-table", DataTable)
        table.focus()

    def setup_table(self) -> None:
        """Set up the data table columns."""
        table = self.query_one("#template-table", DataTable)
        table.add_columns(
            "Template",
            "Description",
            "Repositories",
            "Last Used",
        )
        table.cursor_type = "row"

    def load_usage_data(self) -> None:
        """Load usage tracking data."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file) as f:
                    self.usage_data = json.load(f)
            except Exception:
                self.usage_data = {}

    def save_usage_data(self) -> None:
        """Save usage tracking data."""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, "w") as f:
            json.dump(self.usage_data, f, indent=2)

    def load_templates(self) -> None:
        """Load all available templates."""
        self.templates = []
        template_dir = Path("templates")
        
        if not template_dir.exists():
            return
            
        for template_file in sorted(template_dir.glob("*.yaml")):
            try:
                with open(template_file) as f:
                    data = yaml.safe_load(f)
                
                # Add file path to template data
                data["_filepath"] = str(template_file)
                self.templates.append(data)
            except Exception as e:
                console.print(f"[red]Error loading {template_file}: {e}[/red]")

        # Sort by last usage (most recent first)
        self.templates.sort(
            key=lambda t: self.usage_data.get(t["_filepath"], {}).get("last_used", ""),
            reverse=True
        )

    def update_display(self) -> None:
        """Update the display with templates."""
        table = self.query_one("#template-table", DataTable)
        table.clear()
        
        for template in self.templates:
            filepath = template["_filepath"]
            usage = self.usage_data.get(filepath, {})
            
            # Format last used date
            last_used = usage.get("last_used", "")
            if last_used:
                try:
                    dt = datetime.fromisoformat(last_used)
                    last_used_text = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    last_used_text = "Never"
            else:
                last_used_text = "Never"
            
            # Count repositories
            repo_count = len(template.get("repositories", []))
            repo_text = f"{repo_count} repos"
            
            # Get description
            description = template.get("description", "No description")
            if len(description) > 50:
                description = description[:47] + "..."
            
            table.add_row(
                template.get("name", "Unnamed"),
                description,
                repo_text,
                last_used_text,
                key=filepath,
            )

    def get_selected_template(self) -> str | None:
        """Get the currently selected template filepath."""
        table = self.query_one("#template-table", DataTable)
        if table.row_count == 0:
            return None
        
        # Get the current cursor row
        cursor_row = table.cursor_coordinate.row
        if cursor_row >= 0 and cursor_row < len(self.templates):
            return str(self.templates[cursor_row]["_filepath"])
        return None

    def action_select(self) -> None:
        """Select the current template and launch tracker."""
        template_path = self.get_selected_template()
        if not template_path:
            return
        
        # Update usage data
        self.usage_data[template_path] = {
            "last_used": datetime.now().isoformat(),
            "use_count": self.usage_data.get(template_path, {}).get("use_count", 0) + 1
        }
        self.save_usage_data()
        
        # Exit and return selected template
        self.exit(result=template_path)

    def action_refresh(self) -> None:
        """Refresh the template list."""
        self.load_templates()
        self.update_display()

    @on(DataTable.RowSelected)
    def on_datatable_row_selected(self, event) -> None:
        """Handle row selection by double-click or Enter."""
        if event.row_key and event.row_key.value:
            # Update usage data
            template_path = event.row_key.value
            self.usage_data[template_path] = {
                "last_used": datetime.now().isoformat(),
                "use_count": self.usage_data.get(template_path, {}).get("use_count", 0) + 1
            }
            self.save_usage_data()
            
            # Exit and return selected template
            self.exit(result=template_path)


def run_template_selector() -> str | None:
    """Run the template selector and return selected template path."""
    app = TemplateSelectorApp()
    return app.run()