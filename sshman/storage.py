"""Storage layer for loading and saving connections."""

import json
from pathlib import Path

from .models import AppConfig, Connection


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
