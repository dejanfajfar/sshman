"""Tests for the storage module."""

from pathlib import Path

import pytest

from sshman.models import AppConfig, Connection
from sshman.storage import (
    add_connection,
    delete_connection,
    get_connections,
    load_config,
    save_config,
    update_connection,
)


@pytest.fixture
def temp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".config" / "sshman"
    config_dir.mkdir(parents=True)

    # Patch the get_config_dir function to use temp directory
    monkeypatch.setattr(
        "sshman.storage.get_config_dir",
        lambda: config_dir,
    )

    return config_dir


class TestStorage:
    """Tests for storage functions."""

    def test_load_config_empty(self, temp_config_dir: Path) -> None:
        """Test loading config when no file exists."""
        config = load_config()

        assert config.version == "1.0"
        assert config.connections == []

    def test_save_and_load_config(self, temp_config_dir: Path) -> None:
        """Test saving and loading config."""
        conn = Connection(name="test", hostname="example.com")
        config = AppConfig(connections=[conn])

        save_config(config)
        loaded = load_config()

        assert len(loaded.connections) == 1
        assert loaded.connections[0].name == "test"
        assert loaded.connections[0].hostname == "example.com"

    def test_add_connection(self, temp_config_dir: Path) -> None:
        """Test adding a connection."""
        conn = Connection(name="test", hostname="example.com")

        add_connection(conn)
        connections = get_connections()

        assert len(connections) == 1
        assert connections[0].name == "test"

    def test_add_multiple_connections(self, temp_config_dir: Path) -> None:
        """Test adding multiple connections."""
        conn1 = Connection(name="server1", hostname="example1.com")
        conn2 = Connection(name="server2", hostname="example2.com")

        add_connection(conn1)
        add_connection(conn2)
        connections = get_connections()

        assert len(connections) == 2
        assert connections[0].name == "server1"
        assert connections[1].name == "server2"

    def test_update_connection(self, temp_config_dir: Path) -> None:
        """Test updating a connection."""
        conn = Connection(name="test", hostname="old.example.com")
        add_connection(conn)

        updated = Connection(name="test", hostname="new.example.com")
        update_connection(0, updated)

        connections = get_connections()
        assert connections[0].hostname == "new.example.com"

    def test_delete_connection(self, temp_config_dir: Path) -> None:
        """Test deleting a connection."""
        conn1 = Connection(name="server1", hostname="example1.com")
        conn2 = Connection(name="server2", hostname="example2.com")
        add_connection(conn1)
        add_connection(conn2)

        delete_connection(0)

        connections = get_connections()
        assert len(connections) == 1
        assert connections[0].name == "server2"

    def test_load_corrupted_config(self, temp_config_dir: Path) -> None:
        """Test loading corrupted config returns default."""
        config_path = temp_config_dir / "connections.json"
        config_path.write_text("not valid json", encoding="utf-8")

        config = load_config()

        assert config.connections == []
