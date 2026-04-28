"""Tests for the ssh_agent module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from sshman.models import Connection
from sshman.ssh_agent import ensure_key_in_agent, is_agent_running, is_key_loaded

# ---------------------------------------------------------------------------
# is_agent_running
# ---------------------------------------------------------------------------


def test_is_agent_running_when_sock_set():
    with patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock"}):
        assert is_agent_running() is True


def test_is_agent_running_when_sock_missing():
    env = {k: v for k, v in __import__("os").environ.items() if k != "SSH_AUTH_SOCK"}
    with patch.dict("os.environ", env, clear=True):
        assert is_agent_running() is False


# ---------------------------------------------------------------------------
# is_key_loaded
# ---------------------------------------------------------------------------


def _make_run(returncode: int, stdout: str = "") -> MagicMock:
    """Helper: create a mock CompletedProcess."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_is_key_loaded_true_when_fingerprint_matches():
    list_output = "2048 SHA256:abcDEF key-comment (RSA)\n"
    keygen_output = "2048 SHA256:abcDEF user@host (RSA)\n"

    with patch(
        "sshman.ssh_agent.subprocess.run",
        side_effect=[_make_run(0, list_output), _make_run(0, keygen_output)],
    ):
        assert is_key_loaded("~/.ssh/id_rsa") is True


def test_is_key_loaded_false_when_fingerprint_differs():
    list_output = "2048 SHA256:XXXXXX other-key (RSA)\n"
    keygen_output = "2048 SHA256:abcDEF user@host (RSA)\n"

    with patch(
        "sshman.ssh_agent.subprocess.run",
        side_effect=[_make_run(0, list_output), _make_run(0, keygen_output)],
    ):
        assert is_key_loaded("~/.ssh/id_rsa") is False


def test_is_key_loaded_false_when_agent_unavailable():
    with patch(
        "sshman.ssh_agent.subprocess.run",
        side_effect=[_make_run(2, "")],
    ):
        assert is_key_loaded("~/.ssh/id_rsa") is False


def test_is_key_loaded_false_when_ssh_add_not_found():
    with patch(
        "sshman.ssh_agent.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        assert is_key_loaded("~/.ssh/id_rsa") is False


def test_is_key_loaded_false_when_keygen_fails():
    list_output = "2048 SHA256:abcDEF key-comment (RSA)\n"

    with patch(
        "sshman.ssh_agent.subprocess.run",
        side_effect=[_make_run(0, list_output), _make_run(1, "")],
    ):
        assert is_key_loaded("~/.ssh/id_rsa") is False


# ---------------------------------------------------------------------------
# ensure_key_in_agent
# ---------------------------------------------------------------------------


def test_ensure_key_in_agent_no_agent():
    env = {k: v for k, v in __import__("os").environ.items() if k != "SSH_AUTH_SOCK"}
    with patch.dict("os.environ", env, clear=True):
        ok, msg = ensure_key_in_agent("~/.ssh/id_rsa")
    assert ok is False
    assert "SSH_AUTH_SOCK" in msg


def test_ensure_key_in_agent_already_loaded():
    with (
        patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/agent.sock"}),
        patch("sshman.ssh_agent.is_key_loaded", return_value=True),
    ):
        ok, msg = ensure_key_in_agent("~/.ssh/id_rsa")
    assert ok is True
    assert msg == ""


def test_ensure_key_in_agent_adds_key_successfully():
    with (
        patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/agent.sock"}),
        patch("sshman.ssh_agent.is_key_loaded", return_value=False),
        patch(
            "sshman.ssh_agent.subprocess.run",
            return_value=_make_run(0),
        ) as mock_run,
    ):
        ok, msg = ensure_key_in_agent("~/.ssh/id_rsa")

    assert ok is True
    assert msg == ""
    called_cmd = mock_run.call_args[0][0]
    assert "ssh-add" in called_cmd
    assert "~/.ssh/id_rsa" in called_cmd


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only flag")
def test_ensure_key_in_agent_uses_apple_keychain_on_macos():
    with (
        patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/agent.sock"}),
        patch("sshman.ssh_agent.is_key_loaded", return_value=False),
        patch(
            "sshman.ssh_agent.subprocess.run",
            return_value=_make_run(0),
        ) as mock_run,
    ):
        ensure_key_in_agent("~/.ssh/id_rsa")

    called_cmd = mock_run.call_args[0][0]
    assert "--apple-use-keychain" in called_cmd


def test_ensure_key_in_agent_ssh_add_failure():
    with (
        patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/agent.sock"}),
        patch("sshman.ssh_agent.is_key_loaded", return_value=False),
        patch(
            "sshman.ssh_agent.subprocess.run",
            return_value=_make_run(1),
        ),
    ):
        ok, msg = ensure_key_in_agent("~/.ssh/id_rsa")

    assert ok is False
    assert "1" in msg


def test_ensure_key_in_agent_ssh_add_not_found():
    with (
        patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/agent.sock"}),
        patch("sshman.ssh_agent.is_key_loaded", return_value=False),
        patch("sshman.ssh_agent.subprocess.run", side_effect=FileNotFoundError),
    ):
        ok, msg = ensure_key_in_agent("~/.ssh/id_rsa")

    assert ok is False
    assert "ssh-add" in msg


# ---------------------------------------------------------------------------
# Connection.ssh_add_command
# ---------------------------------------------------------------------------


def test_ssh_add_command_none_when_disabled():
    conn = Connection(
        name="test", hostname="example.com", identity_file="~/.ssh/id_rsa"
    )
    assert conn.ssh_add_command() is None


def test_ssh_add_command_none_when_no_identity():
    conn = Connection(name="test", hostname="example.com", auto_add_key=True)
    assert conn.ssh_add_command() is None


def test_ssh_add_command_includes_identity_file():
    conn = Connection(
        name="test",
        hostname="example.com",
        identity_file="~/.ssh/id_ed25519",
        auto_add_key=True,
    )
    cmd = conn.ssh_add_command()
    assert cmd is not None
    assert "ssh-add" in cmd
    assert "~/.ssh/id_ed25519" in cmd


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only flag")
def test_ssh_add_command_apple_keychain_on_macos():
    conn = Connection(
        name="test",
        hostname="example.com",
        identity_file="~/.ssh/id_rsa",
        auto_add_key=True,
    )
    cmd = conn.ssh_add_command()
    assert cmd is not None
    assert "--apple-use-keychain" in cmd


@pytest.mark.skipif(sys.platform == "darwin", reason="Non-macOS test")
def test_ssh_add_command_no_apple_keychain_on_linux():
    conn = Connection(
        name="test",
        hostname="example.com",
        identity_file="~/.ssh/id_rsa",
        auto_add_key=True,
    )
    cmd = conn.ssh_add_command()
    assert cmd is not None
    assert "--apple-use-keychain" not in cmd
