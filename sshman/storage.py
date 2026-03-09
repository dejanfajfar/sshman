"""Storage layer for loading and saving connections."""

import json
from pathlib import Path

from .models import AppConfig, Connection, HistoryConfig, HistoryEntry


def get_config_dir() -> Path:
    """Get the sshman config directory, creating it if needed."""
    config_dir = Path.home() / ".config" / "sshman"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the connections.json file."""
    return get_config_dir() / "connections.json"


def load_config() -> AppConfig:
    """Load the app config from disk, or return default if not exists."""
    config_path = get_config_path()

    if not config_path.exists():
        return AppConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        # If config is corrupted, return default
        return AppConfig()


def save_config(config: AppConfig) -> None:
    """Save the app config to disk."""
    config_path = get_config_path()
    config_path.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )


def add_connection(connection: Connection) -> None:
    """Add a new connection to storage."""
    config = load_config()
    config.connections.append(connection)
    save_config(config)


def update_connection(index: int, connection: Connection) -> None:
    """Update an existing connection by index."""
    config = load_config()
    if 0 <= index < len(config.connections):
        config.connections[index] = connection
        save_config(config)


def delete_connection(index: int) -> None:
    """Delete a connection by index."""
    config = load_config()
    if 0 <= index < len(config.connections):
        config.connections.pop(index)
        save_config(config)


def get_connections() -> list[Connection]:
    """Get all saved connections."""
    return load_config().connections


# --- History storage functions ---


def get_history_path() -> Path:
    """Get the path to the history.json file."""
    return get_config_dir() / "history.json"


def load_history() -> HistoryConfig:
    """Load the history config from disk, or return default if not exists."""
    history_path = get_history_path()

    if not history_path.exists():
        return HistoryConfig()

    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        return HistoryConfig.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        # If history is corrupted, return default
        return HistoryConfig()


def save_history(config: HistoryConfig) -> None:
    """Save the history config to disk."""
    history_path = get_history_path()
    history_path.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )


def add_history_entry(entry: HistoryEntry) -> None:
    """Add a new history entry to storage."""
    config = load_history()
    # Add new entry at the beginning (most recent first)
    config.entries.insert(0, entry)
    save_history(config)


def get_history_entries() -> list[HistoryEntry]:
    """Get all history entries (most recent first)."""
    return load_history().entries
