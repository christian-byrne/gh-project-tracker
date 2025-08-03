"""Command-line interface for GitHub Issue Tracker."""

from pathlib import Path

import click

from .template_selector import run_template_selector
from .tui import IssueTrackerApp


@click.command()
@click.argument(
    "template",
    type=click.Path(exists=True, path_type=Path),
    required=False,
)
def main(template: Path | None) -> None:
    """Run the GitHub Issue Tracker.
    
    If no template is specified, opens a template selection screen.
    
    Args:
        template: Path to YAML template file (optional)
    """
    if template:
        template_path = str(template)
    else:
        # Run template selector
        selected = run_template_selector()
        if not selected:
            click.echo("No template selected.")
            return
        template_path = selected
    
    # Run the issue tracker
    app = IssueTrackerApp(template_path)
    app.run()


if __name__ == "__main__":
    main()