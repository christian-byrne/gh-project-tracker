"""Filter configuration modal for runtime filter changes."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label

from .models import QueryTemplate


class FilterConfigModal(ModalScreen):
    """Modal for configuring filters at runtime."""

    CSS = """
    #filter-config-modal {
        width: 80;
        height: 30;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }
    
    .filter-section {
        height: auto;
        margin: 1 0;
    }
    
    .filter-row {
        height: 3;
        align: left middle;
    }
    
    .button-row {
        height: 3;
        align: center middle;
        margin-top: 2;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    
    Select {
        width: 20;
    }
    
    Input {
        width: 30;
    }
    """

    def __init__(self, template: QueryTemplate):
        """Initialize filter config modal."""
        super().__init__()
        self.template = template
        self.temp_state = template.state
        self.temp_include_discussions = template.include_discussions
        self.show_closed = template.state in ["closed", "all"]
        self.show_open = template.state in ["open", "all"]

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        yield Container(
            Label("Configure Filters", classes="title"),
            
            Vertical(
                Label("Issue State:"),
                Horizontal(
                    Checkbox("Open", value=self.show_open, id="show-open"),
                    Checkbox("Closed", value=self.show_closed, id="show-closed"),
                    classes="filter-row"
                ),
                classes="filter-section"
            ),
            
            Vertical(
                Label("Include:"),
                Checkbox(
                    "Discussions", 
                    value=self.temp_include_discussions, 
                    id="include-discussions"
                ),
                classes="filter-section"
            ),
            
            Vertical(
                Label("Save Template:"),
                Horizontal(
                    Input(
                        placeholder="Enter new template name...",
                        id="save-template-name"
                    ),
                    Button("Save As", variant="primary", id="save-as-template"),
                    classes="filter-row"
                ),
                classes="filter-section"
            ),
            
            Horizontal(
                Button("Apply", variant="primary", id="apply-filters"),
                Button("Cancel", variant="default", id="cancel-filters"),
                classes="button-row",
            ),
            id="filter-config-modal",
        )

    @on(Checkbox.Changed, "#show-open")
    def on_show_open_changed(self, event: Checkbox.Changed) -> None:
        """Handle open checkbox change."""
        self.show_open = event.value
        self._update_state()

    @on(Checkbox.Changed, "#show-closed")
    def on_show_closed_changed(self, event: Checkbox.Changed) -> None:
        """Handle closed checkbox change."""
        self.show_closed = event.value
        self._update_state()

    def _update_state(self) -> None:
        """Update temp state based on checkboxes."""
        if self.show_open and self.show_closed:
            self.temp_state = "all"
        elif self.show_open:
            self.temp_state = "open"
        elif self.show_closed:
            self.temp_state = "closed"
        else:
            # At least one must be selected
            if self.temp_state == "open":
                self.show_open = True
                self.query_one("#show-open", Checkbox).value = True
            else:
                self.show_closed = True
                self.query_one("#show-closed", Checkbox).value = True

    @on(Checkbox.Changed, "#include-discussions")
    def on_include_discussions_changed(self, event: Checkbox.Changed) -> None:
        """Handle discussions checkbox change."""
        self.temp_include_discussions = event.value

    @on(Button.Pressed, "#save-as-template")
    def save_as_template(self) -> None:
        """Save current filters as new template."""
        name_input = self.query_one("#save-template-name", Input)
        if name_input.value.strip():
            # Create new template with current settings
            new_template = self.template.model_copy(deep=True)
            new_template.name = name_input.value.strip()
            new_template.state = self.temp_state
            new_template.include_discussions = self.temp_include_discussions
            
            # Return the new template
            self.dismiss(("save_as", new_template))

    @on(Button.Pressed, "#apply-filters")
    def apply_filters(self) -> None:
        """Apply the filters and close modal."""
        self.dismiss(("apply", {
            "state": self.temp_state,
            "include_discussions": self.temp_include_discussions
        }))

    @on(Button.Pressed, "#cancel-filters")
    def cancel_filters(self) -> None:
        """Cancel and close modal."""
        self.dismiss(None)