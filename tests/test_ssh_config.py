"""Tests for SSH config parsing."""

from pathlib import Path

import pytest

from sshman.ssh_config import parse_ssh_config


@pytest.fixture
def temp_ssh_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary SSH config file for testing."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    config_path = ssh_dir / "config"

    monkeypatch.setattr(
        "sshman.ssh_config.get_ssh_config_path",
        lambda: config_path,
    )

    return config_path


class TestSSHConfigParser:
    """Tests for SSH config parsing."""

    def test_parse_empty_config(self, temp_ssh_config: Path) -> None:
        """Test parsing empty config file."""
        temp_ssh_config.write_text("", encoding="utf-8")

        connections = parse_ssh_config()

        assert connections == []

    def test_parse_nonexistent_config(self, temp_ssh_config: Path) -> None:
        """Test parsing when config file doesn't exist."""
        # Don't create the file
        temp_ssh_config.unlink(missing_ok=True)

        connections = parse_ssh_config()

        assert connections == []

    def test_parse_simple_host(self, temp_ssh_config: Path) -> None:
        """Test parsing a simple host entry."""
        temp_ssh_config.write_text(
            """
Host myserver
    HostName example.com
    User admin
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        assert connections[0].name == "myserver"
        assert connections[0].hostname == "example.com"
        assert connections[0].user == "admin"
        assert connections[0].port == 22

    def test_parse_host_with_port(self, temp_ssh_config: Path) -> None:
        """Test parsing host with custom port."""
        temp_ssh_config.write_text(
            """
Host myserver
    HostName example.com
    Port 2222
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        assert connections[0].port == 2222

    def test_parse_host_with_identity_file(self, temp_ssh_config: Path) -> None:
        """Test parsing host with identity file."""
        temp_ssh_config.write_text(
            """
Host myserver
    HostName example.com
    IdentityFile ~/.ssh/mykey
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        # The path should be expanded
        assert connections[0].identity_file is not None
        assert "mykey" in connections[0].identity_file

    def test_parse_multiple_hosts(self, temp_ssh_config: Path) -> None:
        """Test parsing multiple host entries."""
        temp_ssh_config.write_text(
            """
Host server1
    HostName example1.com
    User user1

Host server2
    HostName example2.com
    User user2
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 2
        assert connections[0].name == "server1"
        assert connections[1].name == "server2"

    def test_skip_wildcard_hosts(self, temp_ssh_config: Path) -> None:
        """Test that wildcard hosts are skipped."""
        temp_ssh_config.write_text(
            """
Host *
    ServerAliveInterval 60

Host *.example.com
    User deploy

Host myserver
    HostName example.com
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        assert connections[0].name == "myserver"

    def test_parse_with_comments(self, temp_ssh_config: Path) -> None:
        """Test parsing config with comments."""
        temp_ssh_config.write_text(
            """
# This is a comment
Host myserver
    HostName example.com  # inline comment
    User admin
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        assert connections[0].hostname == "example.com"

    def test_host_without_hostname_uses_alias(self, temp_ssh_config: Path) -> None:
        """Test that host alias is used when HostName is not specified."""
        temp_ssh_config.write_text(
            """
Host example.com
    User admin
""",
            encoding="utf-8",
        )

        connections = parse_ssh_config()

        assert len(connections) == 1
        assert connections[0].name == "example.com"
        assert connections[0].hostname == "example.com"
