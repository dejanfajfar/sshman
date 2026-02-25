"""Tests for the Connection model."""

import pytest

from sshman.models import Connection


class TestConnection:
    """Tests for the Connection model."""

    def test_connection_creation(self) -> None:
        """Test creating a basic connection."""
        conn = Connection(name="test-server", hostname="192.168.1.1")

        assert conn.name == "test-server"
        assert conn.hostname == "192.168.1.1"
        assert conn.user is None
        assert conn.port == 22
        assert conn.identity_file is None

    def test_connection_with_all_fields(self) -> None:
        """Test creating a connection with all fields populated."""
        conn = Connection(
            name="prod-server",
            hostname="example.com",
            user="admin",
            port=2222,
            identity_file="~/.ssh/id_rsa",
        )

        assert conn.name == "prod-server"
        assert conn.hostname == "example.com"
        assert conn.user == "admin"
        assert conn.port == 2222
        assert conn.identity_file == "~/.ssh/id_rsa"

    def test_ssh_command_basic(self) -> None:
        """Test SSH command generation for basic connection."""
        conn = Connection(name="test", hostname="example.com")

        cmd = conn.ssh_command()

        assert cmd == ["ssh", "example.com"]

    def test_ssh_command_with_user(self) -> None:
        """Test SSH command generation with user."""
        conn = Connection(name="test", hostname="example.com", user="root")

        cmd = conn.ssh_command()

        assert cmd == ["ssh", "root@example.com"]

    def test_ssh_command_with_port(self) -> None:
        """Test SSH command generation with custom port."""
        conn = Connection(name="test", hostname="example.com", port=2222)

        cmd = conn.ssh_command()

        assert cmd == ["ssh", "-p", "2222", "example.com"]

    def test_ssh_command_with_identity_file(self) -> None:
        """Test SSH command generation with identity file."""
        conn = Connection(
            name="test",
            hostname="example.com",
            identity_file="~/.ssh/mykey",
        )

        cmd = conn.ssh_command()

        assert cmd == ["ssh", "-i", "~/.ssh/mykey", "example.com"]

    def test_ssh_command_full(self) -> None:
        """Test SSH command generation with all options."""
        conn = Connection(
            name="test",
            hostname="example.com",
            user="admin",
            port=2222,
            identity_file="~/.ssh/mykey",
        )

        cmd = conn.ssh_command()

        assert cmd == [
            "ssh",
            "-p",
            "2222",
            "-i",
            "~/.ssh/mykey",
            "admin@example.com",
        ]

    def test_display_target_basic(self) -> None:
        """Test display target for basic connection."""
        conn = Connection(name="test", hostname="example.com")

        assert conn.display_target() == "example.com"

    def test_display_target_with_user(self) -> None:
        """Test display target with user."""
        conn = Connection(name="test", hostname="example.com", user="admin")

        assert conn.display_target() == "admin@example.com"

    def test_display_target_with_port(self) -> None:
        """Test display target with custom port."""
        conn = Connection(name="test", hostname="example.com", port=2222)

        assert conn.display_target() == "example.com:2222"

    def test_display_target_full(self) -> None:
        """Test display target with user and port."""
        conn = Connection(
            name="test",
            hostname="example.com",
            user="admin",
            port=2222,
        )

        assert conn.display_target() == "admin@example.com:2222"

    def test_port_validation_min(self) -> None:
        """Test that port must be at least 1."""
        with pytest.raises(ValueError):
            Connection(name="test", hostname="example.com", port=0)

    def test_port_validation_max(self) -> None:
        """Test that port must be at most 65535."""
        with pytest.raises(ValueError):
            Connection(name="test", hostname="example.com", port=65536)
