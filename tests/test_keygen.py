"""Tests for the keygen module."""

from unittest.mock import MagicMock, patch

from sshman.keygen import generate_key


def _make_run(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    """Return a mock CompletedProcess-like object."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------


def test_generate_key_fails_if_file_already_exists(tmp_path):
    existing = tmp_path / "id_ed25519"
    existing.write_text("existing key")

    ok, msg = generate_key(str(existing))
    assert ok is False
    assert "already exists" in msg


# ---------------------------------------------------------------------------
# Successful generation
# ---------------------------------------------------------------------------


def test_generate_key_success(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        ok, msg = generate_key(str(key_path))

    assert ok is True
    assert msg == ""
    mock_run.assert_called_once()


def test_generate_key_uses_ed25519(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        generate_key(str(key_path))

    cmd = mock_run.call_args[0][0]
    assert "-t" in cmd
    assert "ed25519" in cmd


def test_generate_key_passes_key_path(tmp_path):
    key_path = tmp_path / "sshman_myserver"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        generate_key(str(key_path))

    cmd = mock_run.call_args[0][0]
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert cmd[idx + 1] == str(key_path)


def test_generate_key_no_passphrase(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        generate_key(str(key_path), passphrase="")

    cmd = mock_run.call_args[0][0]
    assert "-N" in cmd
    idx = cmd.index("-N")
    assert cmd[idx + 1] == ""


def test_generate_key_with_passphrase(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        generate_key(str(key_path), passphrase="s3cr3t")

    cmd = mock_run.call_args[0][0]
    assert "-N" in cmd
    idx = cmd.index("-N")
    assert cmd[idx + 1] == "s3cr3t"


def test_generate_key_expands_tilde(tmp_path, monkeypatch):
    """The path passed to ssh-keygen must be fully expanded (no ~)."""
    # Redirect ~ to a temp dir so we don't touch the real ~/.ssh
    monkeypatch.setenv("HOME", str(tmp_path))

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(0),
    ) as mock_run:
        generate_key("~/sshman_test")

    cmd = mock_run.call_args[0][0]
    idx = cmd.index("-f")
    assert "~" not in cmd[idx + 1], (
        "Tilde should be expanded before passing to ssh-keygen"
    )


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def test_generate_key_ssh_keygen_failure_uses_stderr(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(1, stdout="", stderr="Permission denied"),
    ):
        ok, msg = generate_key(str(key_path))

    assert ok is False
    assert "Permission denied" in msg


def test_generate_key_ssh_keygen_failure_falls_back_to_stdout(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        return_value=_make_run(1, stdout="some output", stderr=""),
    ):
        ok, msg = generate_key(str(key_path))

    assert ok is False
    assert "some output" in msg


def test_generate_key_not_found(tmp_path):
    key_path = tmp_path / "sshman_test"

    with patch(
        "sshman.keygen.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        ok, msg = generate_key(str(key_path))

    assert ok is False
    assert "ssh-keygen" in msg
    assert "PATH" in msg
