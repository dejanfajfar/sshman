"""Main Textual TUI application for sshman."""

import subprocess

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from .models import Connection
from .ssh_config import parse_ssh_config
from .storage import (
    add_connection,
    delete_connection,
    get_connections,
    load_config,
    save_config,
    update_connection,
)


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal screen for confirming deletion."""

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    
    #confirm-dialog {
        width: 50;
        height: 10;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #confirm-buttons {
        margin-top: 1;
        align: center middle;
    }
    
    #confirm-buttons Button {
        margin: 0 2;
    }
    """

    def __init__(self, connection_name: str) -> None:
        super().__init__()
        self.connection_name = connection_name

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(f"Delete '{self.connection_name}'?")
            with Horizontal(id="confirm-buttons"):
                yield Button("Delete", variant="error", id="confirm-yes")
                yield Button("Cancel", variant="primary", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def confirm_delete(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def cancel_delete(self) -> None:
        self.dismiss(False)


class ConnectionFormScreen(ModalScreen[Connection | None]):
    """Modal screen for adding/editing a connection."""

    CSS = """
    ConnectionFormScreen {
        align: center middle;
    }
    
    #form-container {
        width: 60;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    .form-row {
        height: 3;
        margin-bottom: 1;
    }
    
    .form-row Label {
        width: 15;
        padding-top: 1;
    }
    
    .form-row Input {
        width: 1fr;
    }
    
    #form-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    
    #form-buttons Button {
        margin: 0 2;
    }
    
    #form-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, connection: Connection | None = None) -> None:
        super().__init__()
        self.connection = connection
        self.is_edit = connection is not None

    def on_mount(self) -> None:
        """Focus the first input field when the form opens."""
        self.query_one("#input-name", Input).focus()

    def compose(self) -> ComposeResult:
        title = "Edit Connection" if self.is_edit else "Add Connection"
        conn = self.connection

        with Container(id="form-container"):
            yield Label(title, id="form-title")

            with Horizontal(classes="form-row"):
                yield Label("Name:")
                yield Input(
                    value=conn.name if conn else "",
                    placeholder="e.g., my-server",
                    id="input-name",
                )

            with Horizontal(classes="form-row"):
                yield Label("Hostname:")
                yield Input(
                    value=conn.hostname if conn else "",
                    placeholder="e.g., 192.168.1.100",
                    id="input-hostname",
                )

            with Horizontal(classes="form-row"):
                yield Label("User:")
                yield Input(
                    value=conn.user or "" if conn else "",
                    placeholder="e.g., root",
                    id="input-user",
                )

            with Horizontal(classes="form-row"):
                yield Label("Port:")
                yield Input(
                    value=str(conn.port) if conn else "22",
                    placeholder="22",
                    id="input-port",
                )

            with Horizontal(classes="form-row"):
                yield Label("Identity File:")
                yield Input(
                    value=conn.identity_file or "" if conn else "",
                    placeholder="e.g., ~/.ssh/id_rsa",
                    id="input-identity",
                )

            with Horizontal(id="form-buttons"):
                yield Button("Save", variant="primary", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    @on(Button.Pressed, "#btn-save")
    def save_connection(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        hostname = self.query_one("#input-hostname", Input).value.strip()
        user = self.query_one("#input-user", Input).value.strip() or None
        port_str = self.query_one("#input-port", Input).value.strip()
        identity = self.query_one("#input-identity", Input).value.strip() or None

        # Validation
        if not name or not hostname:
            self.notify("Name and Hostname are required", severity="error")
            return

        try:
            port = int(port_str) if port_str else 22
            if not (1 <= port <= 65535):
                raise ValueError("Port out of range")
        except ValueError:
            self.notify("Invalid port number", severity="error")
            return

        connection = Connection(
            name=name,
            hostname=hostname,
            user=user,
            port=port,
            identity_file=identity,
        )
        self.dismiss(connection)

    @on(Button.Pressed, "#btn-cancel")
    def cancel_form(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ImportScreen(ModalScreen[list[Connection]]):
    """Modal screen for importing from ~/.ssh/config."""

    CSS = """
    ImportScreen {
        align: center middle;
    }
    
    #import-container {
        width: 80%;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #import-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    #import-table {
        height: 1fr;
    }
    
    #import-buttons {
        height: 3;
        align: center middle;
    }
    
    #import-buttons Button {
        margin: 0 2;
    }
    
    #import-info {
        margin-bottom: 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.parsed_connections = parse_ssh_config()
        self.selected_indices: set[int] = set()

    def compose(self) -> ComposeResult:
        with Container(id="import-container"):
            yield Label("Import from ~/.ssh/config", id="import-title")
            yield Label(
                "Select connections to import (space to toggle, enter to confirm)",
                id="import-info",
            )

            table = DataTable(id="import-table", cursor_type="row")
            table.add_columns("", "Name", "Host", "User", "Port")
            yield table

            with Horizontal(id="import-buttons"):
                yield Button("Import Selected", variant="primary", id="btn-import")
                yield Button("Select All", variant="default", id="btn-select-all")
                yield Button("Cancel", variant="default", id="btn-cancel-import")

    def on_mount(self) -> None:
        table = self.query_one("#import-table", DataTable)

        if not self.parsed_connections:
            table.add_row("", "No connections found in ~/.ssh/config", "", "", "")
            return

        for i, conn in enumerate(self.parsed_connections):
            table.add_row(
                "[ ]",
                conn.name,
                conn.hostname,
                conn.user or "-",
                str(conn.port),
                key=str(i),
            )

    @on(DataTable.RowSelected, "#import-table")
    def toggle_selection(self, event: DataTable.RowSelected) -> None:
        if not self.parsed_connections:
            return

        try:
            idx = int(str(event.row_key.value))
        except (ValueError, AttributeError):
            return

        table = self.query_one("#import-table", DataTable)

        if idx in self.selected_indices:
            self.selected_indices.remove(idx)
            check = "[ ]"
        else:
            self.selected_indices.add(idx)
            check = "[x]"

        # Update the checkbox column
        table.update_cell_at(Coordinate(idx, 0), check)

    @on(Button.Pressed, "#btn-select-all")
    def select_all(self) -> None:
        if not self.parsed_connections:
            return

        table = self.query_one("#import-table", DataTable)
        self.selected_indices = set(range(len(self.parsed_connections)))

        for i in range(len(self.parsed_connections)):
            table.update_cell_at(Coordinate(i, 0), "[x]")

    @on(Button.Pressed, "#btn-import")
    def do_import(self) -> None:
        selected = [
            self.parsed_connections[i]
            for i in sorted(self.selected_indices)
            if i < len(self.parsed_connections)
        ]
        self.dismiss(selected)

    @on(Button.Pressed, "#btn-cancel-import")
    def cancel_import(self) -> None:
        self.dismiss([])

    def action_cancel(self) -> None:
        self.dismiss([])


class SSHManApp(App):
    """Main sshman application."""

    TITLE = "sshman"
    SUB_TITLE = "SSH Connection Manager"

    CSS = """
    #main-container {
        height: 1fr;
    }
    
    #search-container {
        height: 3;
        padding: 0 1;
    }
    
    #search-input {
        width: 100%;
    }
    
    #connections-table {
        height: 1fr;
    }
    
    #empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_connection", "Add"),
        Binding("e", "edit_connection", "Edit"),
        Binding("d", "delete_connection", "Delete"),
        Binding("i", "import_config", "Import"),
        Binding("enter", "connect", "Connect"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear Search"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.connections: list[Connection] = []
        self.filtered_connections: list[Connection] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="main-container"):
            with Container(id="search-container"):
                yield Input(placeholder="Search connections...", id="search-input")

            yield DataTable(id="connections-table", cursor_type="row")
            yield Static(
                "No connections yet. Press 'a' to add or 'i' to import.",
                id="empty-message",
            )

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_connections()

    def refresh_connections(self) -> None:
        """Reload connections from storage and update the table."""
        self.connections = get_connections()
        self.filter_connections()

    def filter_connections(self, search: str = "") -> None:
        """Filter connections based on search term."""
        search = search.lower().strip()

        if search:
            self.filtered_connections = [
                c
                for c in self.connections
                if search in c.name.lower()
                or search in c.hostname.lower()
                or (c.user and search in c.user.lower())
            ]
        else:
            self.filtered_connections = self.connections.copy()

        self.update_table()

    def update_table(self) -> None:
        """Update the DataTable with current filtered connections."""
        table = self.query_one("#connections-table", DataTable)
        empty_msg = self.query_one("#empty-message", Static)

        table.clear(columns=True)

        if not self.filtered_connections:
            table.display = False
            empty_msg.display = True
            if self.connections:
                empty_msg.update("No connections match your search.")
            else:
                empty_msg.update(
                    "No connections yet. Press 'a' to add or 'i' to import."
                )
            return

        table.display = True
        empty_msg.display = False

        table.add_columns("Name", "Target", "Identity File")

        for conn in self.filtered_connections:
            table.add_row(
                conn.name,
                conn.display_target(),
                conn.identity_file or "-",
            )

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.filter_connections(event.value)

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.filter_connections("")
        self.query_one("#connections-table", DataTable).focus()

    def get_selected_connection_index(self) -> int | None:
        """Get the index of the currently selected connection in the main list."""
        table = self.query_one("#connections-table", DataTable)

        if not self.filtered_connections:
            return None

        try:
            row_idx = table.cursor_row
            if row_idx < 0 or row_idx >= len(self.filtered_connections):
                return None

            # Find the index in the main connections list
            selected_conn = self.filtered_connections[row_idx]
            return self.connections.index(selected_conn)
        except (ValueError, IndexError):
            return None

    def action_add_connection(self) -> None:
        def handle_result(connection: Connection | None) -> None:
            if connection:
                add_connection(connection)
                self.refresh_connections()
                self.notify(f"Added '{connection.name}'")

        self.push_screen(ConnectionFormScreen(), handle_result)

    def action_edit_connection(self) -> None:
        idx = self.get_selected_connection_index()
        if idx is None:
            self.notify("No connection selected", severity="warning")
            return

        conn = self.connections[idx]

        def handle_result(updated: Connection | None) -> None:
            if updated:
                update_connection(idx, updated)
                self.refresh_connections()
                self.notify(f"Updated '{updated.name}'")

        self.push_screen(ConnectionFormScreen(conn), handle_result)

    def action_delete_connection(self) -> None:
        idx = self.get_selected_connection_index()
        if idx is None:
            self.notify("No connection selected", severity="warning")
            return

        conn = self.connections[idx]

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                delete_connection(idx)
                self.refresh_connections()
                self.notify(f"Deleted '{conn.name}'")

        self.push_screen(ConfirmDeleteScreen(conn.name), handle_result)

    def action_import_config(self) -> None:
        def handle_result(imported: list[Connection] | None) -> None:
            if imported:
                config = load_config()
                existing_names = {c.name for c in config.connections}

                added = 0
                for conn in imported:
                    if conn.name not in existing_names:
                        config.connections.append(conn)
                        existing_names.add(conn.name)
                        added += 1

                save_config(config)
                self.refresh_connections()
                self.notify(f"Imported {added} connection(s)")

        self.push_screen(ImportScreen(), handle_result)

    def action_connect(self) -> None:
        idx = self.get_selected_connection_index()
        if idx is None:
            self.notify("No connection selected", severity="warning")
            return

        conn = self.connections[idx]
        ssh_cmd = conn.ssh_command()

        # Exit the TUI and run SSH
        self.exit(result=ssh_cmd)


def run() -> None:
    """Run the sshman application."""
    app = SSHManApp()
    result = app.run()

    # If user selected a connection, run SSH
    if result:
        subprocess.run(result)


if __name__ == "__main__":
    run()
