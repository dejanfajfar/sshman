"""Main Textual TUI application for sshman."""

import subprocess
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from .docker import detect_shell, get_running_containers, is_docker_available
from .keygen import generate_key
from .models import Connection, DockerContainer, HistoryEntry
from .ssh_agent import ensure_key_in_agent
from .ssh_config import parse_ssh_config
from .storage import (
    add_connection,
    add_history_entry,
    delete_connection,
    get_connections,
    get_history_entries,
    load_config,
    save_config,
    update_connection,
)


class KeyGenScreen(ModalScreen[str | None]):
    """Modal wizard for generating an Ed25519 SSH key pair.

    Dismisses with the (unexpanded) key path on success, or None on cancel.
    """

    CSS = """
    KeyGenScreen {
        align: center middle;
    }

    #keygen-container {
        width: 64;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #keygen-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .kg-row {
        height: 3;
        margin-bottom: 1;
    }

    .kg-row Label {
        width: 18;
        padding-top: 1;
    }

    .kg-row Input {
        width: 1fr;
    }

    #keygen-error {
        color: $error;
        margin-bottom: 1;
        display: none;
    }

    #keygen-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #keygen-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, connection_name: str) -> None:
        super().__init__()
        # Sanitise the connection name for use in a filename
        safe_name = (
            "".join(
                c if c.isalnum() or c in "-_" else "_" for c in connection_name
            ).strip("_")
            or "key"
        )
        self._suggested_path = f"~/.ssh/sshman_{safe_name}"

    def compose(self) -> ComposeResult:
        with Container(id="keygen-container"):
            yield Label("Generate SSH Key", id="keygen-title")

            with Horizontal(classes="kg-row"):
                yield Label("Key path:")
                yield Input(
                    value=self._suggested_path,
                    placeholder="~/.ssh/sshman_myserver",
                    id="input-keypath",
                )

            with Horizontal(classes="kg-row"):
                yield Label("Passphrase:")
                yield Input(
                    placeholder="Leave empty for no passphrase",
                    password=True,
                    id="input-passphrase",
                )

            with Horizontal(classes="kg-row"):
                yield Label("Confirm passphrase:")
                yield Input(
                    placeholder="Repeat passphrase",
                    password=True,
                    id="input-passphrase2",
                )

            yield Label("", id="keygen-error")

            with Horizontal(id="keygen-buttons"):
                yield Button("Generate", variant="primary", id="btn-generate")
                yield Button("Cancel", variant="default", id="btn-cancel-keygen")

    def on_mount(self) -> None:
        self.query_one("#input-keypath", Input).focus()

    def _show_error(self, message: str) -> None:
        err = self.query_one("#keygen-error", Label)
        err.update(message)
        err.display = True

    @on(Button.Pressed, "#btn-generate")
    def do_generate(self) -> None:
        key_path = self.query_one("#input-keypath", Input).value.strip()
        passphrase = self.query_one("#input-passphrase", Input).value
        passphrase2 = self.query_one("#input-passphrase2", Input).value

        if not key_path:
            self._show_error("Key path is required.")
            return

        if passphrase != passphrase2:
            self._show_error("Passphrases do not match.")
            return

        ok, error = generate_key(key_path, passphrase)
        if ok:
            self.dismiss(key_path)
        else:
            self._show_error(error)

    @on(Button.Pressed, "#btn-cancel-keygen")
    def cancel_keygen(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


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


class ConnectionFormScreen(Screen[Connection | None]):
    """Full-screen form for adding/editing a connection."""

    CSS = """
    ConnectionFormScreen {
        align: center middle;
    }

    #form-container {
        width: 60;
        height: auto;
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

    #btn-generate-key {
        width: auto;
        min-width: 14;
        margin-left: 1;
    }

    .form-row-check {
        height: 3;
        margin-bottom: 1;
    }

    .form-row-check Label {
        width: 15;
        padding-top: 1;
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
                yield Button("Generate Key", id="btn-generate-key", variant="default")

            with Horizontal(classes="form-row-check"):
                yield Label("Auto-add key:")
                yield Checkbox(
                    "Add key to ssh-agent before connecting",
                    value=conn.auto_add_key if conn else False,
                    id="check-auto-add",
                )

            with Horizontal(classes="form-row"):
                yield Label("Description:")
                yield Input(
                    value=conn.description or "" if conn else "",
                    placeholder="e.g., Production web server",
                    id="input-description",
                )

            with Horizontal(classes="form-row"):
                yield Label("Tags:")
                yield Input(
                    value=", ".join(conn.tags) if conn else "",
                    placeholder="e.g., production, web, us-east",
                    id="input-tags",
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
        auto_add_key = self.query_one("#check-auto-add", Checkbox).value
        description = self.query_one("#input-description", Input).value.strip() or None
        tags_raw = self.query_one("#input-tags", Input).value.strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

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

        if auto_add_key and not identity:
            self.notify(
                "Identity File is required when Auto-add key is enabled",
                severity="error",
            )
            return

        connection = Connection(
            name=name,
            hostname=hostname,
            user=user,
            port=port,
            identity_file=identity,
            description=description,
            auto_add_key=auto_add_key,
            tags=tags,
        )
        self.dismiss(connection)

    @on(Button.Pressed, "#btn-cancel")
    def cancel_form(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-generate-key")
    def open_keygen(self) -> None:
        """Open the key-generation wizard and auto-fill the result."""
        name = self.query_one("#input-name", Input).value.strip() or "key"

        def handle_keygen_result(key_path: str | None) -> None:
            if key_path:
                self.query_one("#input-identity", Input).value = key_path
                self.query_one("#check-auto-add", Checkbox).value = True

        self.app.push_screen(KeyGenScreen(name), handle_keygen_result)

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
    
    #history-search-input {
        width: 100%;
    }
    
    #connections-table {
        height: 1fr;
    }
    
    #history-table {
        height: 1fr;
    }
    
    #empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    
    #history-empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    
    TabPane {
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_connection", "Add", show=True),
        Binding("e", "edit_connection", "Edit", show=True),
        Binding("d", "delete_connection", "Delete", show=True),
        Binding("i", "import_config", "Import"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("enter", "connect", "Connect"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear"),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("1", "show_connections", "Connections", show=True),
        Binding("2", "show_history", "History", show=True),
    ]

    def __init__(self, error_message: str | None = None) -> None:
        super().__init__()
        self.connections: list[Connection] = []
        self.filtered_connections: list[Connection] = []
        self.docker_containers: list[DockerContainer] = []
        self.filtered_docker: list[DockerContainer] = []
        self.docker_available: bool = False
        self.startup_error_message: str | None = error_message
        # History tracking
        self.history_entries: list[HistoryEntry] = []
        self.filtered_history: list[HistoryEntry] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(id="tabs"):
            with (
                TabPane("Connections", id="tab-connections"),
                Vertical(id="main-container"),
            ):
                with Container(id="search-container"):
                    yield Input(placeholder="Search connections...", id="search-input")

                yield DataTable(id="connections-table", cursor_type="row")
                yield Static(
                    "No connections yet. Press 'a' to add or 'i' to import.",
                    id="empty-message",
                )

            with TabPane("History", id="tab-history"), Vertical(id="history-container"):
                with Container(id="search-container"):
                    yield Input(
                        placeholder="Search history...", id="history-search-input"
                    )

                yield DataTable(id="history-table", cursor_type="row")
                yield Static(
                    "No connection history yet.",
                    id="history-empty-message",
                )

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.load_history()
        # Focus the search input on startup
        self.query_one("#search-input", Input).focus()
        if self.startup_error_message:
            self.notify(self.startup_error_message, severity="error", timeout=5)

    def action_refresh_all(self) -> None:
        """Action handler for the refresh keybinding."""
        self.refresh_all()
        self.load_history()
        self.notify("Refreshed connections and containers")

    def refresh_all(self) -> None:
        """Reload SSH connections and Docker containers."""
        self.connections = get_connections()
        self.docker_available = is_docker_available()
        self.docker_containers = (
            get_running_containers() if self.docker_available else []
        )
        self.filter_all()

    def refresh_connections(self) -> None:
        """Reload connections from storage and update the table."""
        self.refresh_all()

    # --- Tab navigation methods ---

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        if tabs.active == "tab-connections":
            tabs.active = "tab-history"
            self.query_one("#history-table", DataTable).focus()
        else:
            tabs.active = "tab-connections"
            self.query_one("#connections-table", DataTable).focus()

    def action_show_connections(self) -> None:
        """Switch to the Connections tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-connections"
        # Focus the connections table
        self.query_one("#connections-table", DataTable).focus()

    def action_show_history(self) -> None:
        """Switch to the History tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-history"
        # Focus the history table
        self.query_one("#history-table", DataTable).focus()

    # --- History methods ---

    def load_history(self) -> None:
        """Load history entries from storage."""
        self.history_entries = get_history_entries()
        self.filtered_history = self.history_entries.copy()
        self.update_history_table()

    def filter_history(self, search: str = "") -> None:
        """Filter history entries based on search term."""
        search = search.lower().strip()

        if search:
            self.filtered_history = [
                h
                for h in self.history_entries
                if search in h.connection_name.lower()
                or search in h.connection_target.lower()
            ]
        else:
            self.filtered_history = self.history_entries.copy()

        self.update_history_table()

    def update_history_table(self) -> None:
        """Update the history DataTable with current filtered entries."""
        table = self.query_one("#history-table", DataTable)
        empty_msg = self.query_one("#history-empty-message", Static)

        table.clear(columns=True)

        if len(self.filtered_history) == 0:
            table.display = False
            empty_msg.display = True
            return

        table.display = True
        empty_msg.display = False

        table.add_columns("Name", "Target", "Started At", "Duration", "Status")

        for idx, entry in enumerate(self.filtered_history):
            table.add_row(
                entry.connection_name,
                entry.connection_target,
                entry.format_started_at(),
                entry.format_duration(),
                entry.format_status(),
                key=f"history:{idx}",
            )

    @on(Input.Changed, "#history-search-input")
    def on_history_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes in history tab."""
        self.filter_history(event.value)

    def filter_connections(self, search: str = "") -> None:
        """Filter connections based on search term."""
        self.filter_all(search)

    def filter_all(self, search: str = "") -> None:
        """Filter both SSH connections and Docker containers based on search term."""
        search = search.lower().strip()

        if search:
            self.filtered_connections = [
                c
                for c in self.connections
                if search in c.name.lower()
                or search in c.hostname.lower()
                or (c.user and search in c.user.lower())
            ]
            self.filtered_docker = [
                d
                for d in self.docker_containers
                if search in d.name.lower() or search in d.image.lower()
            ]
        else:
            self.filtered_connections = self.connections.copy()
            self.filtered_docker = self.docker_containers.copy()

        self.update_table()

    def update_table(self) -> None:
        """Update the DataTable with current filtered connections and containers."""
        table = self.query_one("#connections-table", DataTable)
        empty_msg = self.query_one("#empty-message", Static)

        table.clear(columns=True)

        total_items = len(self.filtered_connections) + len(self.filtered_docker)

        if total_items == 0:
            table.display = False
            empty_msg.display = True
            if self.connections or self.docker_containers:
                empty_msg.update("No connections match your search.")
            else:
                empty_msg.update(
                    "No connections yet. Press 'a' to add or 'i' to import."
                )
            return

        table.display = True
        empty_msg.display = False

        table.add_columns("Name", "Tags", "Type", "Target", "Info")

        # Add SSH connections
        for conn in self.filtered_connections:
            idx = self.connections.index(conn)
            info_parts = []
            if conn.description:
                info_parts.append(conn.description)
            if conn.identity_file:
                info_parts.append(f"[{conn.identity_file}]")
            info_str = " ".join(info_parts) if info_parts else "-"
            tags_str = ", ".join(conn.tags) if conn.tags else ""
            table.add_row(
                conn.name,
                tags_str,
                "🔐 SSH",
                conn.display_target(),
                info_str,
                key=f"ssh:{idx}",
            )

        # Add Docker containers
        for container in self.filtered_docker:
            table.add_row(
                container.name,
                "",
                "🐳 Docker",
                container.image,
                container.container_id,
                key=f"docker:{container.container_id}",
            )

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.filter_connections(event.value)

    @on(DataTable.RowSelected, "#connections-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:  # noqa: ARG002
        """Handle Enter key press on a table row to start connection."""
        self.action_connect()

    def action_focus_search(self) -> None:
        """Focus the search input in the active tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        if tabs.active == "tab-history":
            self.query_one("#history-search-input", Input).focus()
        else:
            self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        """Clear search and focus table in the active tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        if tabs.active == "tab-history":
            search_input = self.query_one("#history-search-input", Input)
            search_input.value = ""
            self.filter_history("")
            self.query_one("#history-table", DataTable).focus()
        else:
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            self.filter_connections("")
            self.query_one("#connections-table", DataTable).focus()

    def get_selected_row_key(self) -> str | None:
        """Get the row key of the currently selected row."""
        table = self.query_one("#connections-table", DataTable)

        total_items = len(self.filtered_connections) + len(self.filtered_docker)
        if total_items == 0:
            return None

        try:
            row_idx = table.cursor_row
            if row_idx < 0 or row_idx >= total_items:
                return None

            # Use the cursor coordinate to get the row key
            return str(
                table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            )
        except (ValueError, IndexError, AttributeError):
            return None

    def get_selected_connection_index(self) -> int | None:
        """Get the index of the currently selected connection in the main list."""
        row_key = self.get_selected_row_key()
        if row_key is None:
            return None

        if row_key.startswith("ssh:"):
            try:
                return int(row_key.split(":")[1])
            except (ValueError, IndexError):
                return None

        # If it's a Docker row, return None (not an SSH connection)
        return None

    def action_add_connection(self) -> None:
        def handle_result(connection: Connection | None) -> None:
            if connection:
                add_connection(connection)
                self.refresh_connections()
                self.notify(f"Added '{connection.name}'")

        self.push_screen(ConnectionFormScreen(), handle_result)

    def action_edit_connection(self) -> None:
        row_key = self.get_selected_row_key()
        if row_key is None:
            self.notify("No connection selected", severity="warning")
            return

        if row_key.startswith("docker:"):
            self.notify("Cannot edit Docker containers", severity="warning")
            return

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
        row_key = self.get_selected_row_key()
        if row_key is None:
            self.notify("No connection selected", severity="warning")
            return

        if row_key.startswith("docker:"):
            self.notify("Cannot delete Docker containers from here", severity="warning")
            return

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
        row_key = self.get_selected_row_key()
        if row_key is None:
            self.notify("No connection selected", severity="warning")
            return

        if row_key.startswith("ssh:"):
            try:
                idx = int(row_key.split(":")[1])
                conn = self.connections[idx]
                ssh_cmd = conn.ssh_command()
                # Return dict with command and metadata for history tracking
                self.exit(
                    result={
                        "cmd": ssh_cmd,
                        "name": conn.name,
                        "target": conn.display_target(),
                        "type": "ssh",
                        "identity_file": conn.identity_file,
                        "auto_add_key": conn.auto_add_key,
                    }
                )
            except (ValueError, IndexError):
                self.notify("Invalid selection", severity="error")

        elif row_key.startswith("docker:"):
            container_id = row_key.split(":", 1)[1]
            container = next(
                (c for c in self.docker_containers if c.container_id == container_id),
                None,
            )
            if container:
                shell = detect_shell(container.container_id)
                docker_cmd = container.exec_command(shell)
                # Return dict with command and metadata for history tracking
                self.exit(
                    result={
                        "cmd": docker_cmd,
                        "name": container.name,
                        "target": container.display_target(),
                        "type": "docker",
                    }
                )
            else:
                self.notify("Container not found", severity="error")


def run() -> None:
    """Run the sshman application."""
    error_message: str | None = None

    while True:
        app = SSHManApp(error_message=error_message)
        result = app.run()
        error_message = None  # Clear for next iteration

        # If user quit without selecting a connection, exit
        if not result:
            break

        # Extract command and metadata from result dict
        cmd = result["cmd"]
        connection_name = result["name"]
        connection_target = result["target"]
        connection_type = result["type"]

        # If auto_add_key is requested, ensure the key is loaded in the agent
        # before handing off to ssh. This runs while the terminal is fully
        # available (TUI has already exited), so any passphrase prompt works.
        if result.get("auto_add_key") and result.get("identity_file"):
            ok, agent_err = ensure_key_in_agent(result["identity_file"])
            if not ok:
                print(f"[sshman] Warning: could not add key to agent: {agent_err}")

        # Record start time
        start_time = datetime.now()

        # Run the connection command
        cmd_result = subprocess.run(cmd)

        # Record end time and calculate duration
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        # Determine success and error message
        success = cmd_result.returncode == 0
        error_msg = None
        if not success:
            # Map common SSH exit codes to human-readable messages
            exit_code = cmd_result.returncode
            error_messages = {
                1: "General error",
                2: "Misuse of shell command",
                126: "Command not executable",
                127: "Command not found",
                128: "Invalid exit argument",
                130: "Terminated by Ctrl+C",
                255: "Connection failed (network error, auth failure, or timeout)",
            }
            error_msg = error_messages.get(exit_code, f"Exit code: {exit_code}")

        # Create and save history entry
        entry = HistoryEntry(
            connection_name=connection_name,
            connection_target=connection_target,
            connection_type=connection_type,
            started_at=start_time,
            ended_at=end_time,
            duration_seconds=duration_seconds,
            exit_code=cmd_result.returncode,
            success=success,
            error_message=error_msg,
        )
        add_history_entry(entry)

        # If connection failed, restart app with error message
        if not success:
            cmd_str = " ".join(cmd)
            error_message = f"Connection failed: {cmd_str}"
        # Continue loop to restart app after connection ends


if __name__ == "__main__":
    run()
