"""SSH key generation helpers.

Provides a thin wrapper around ``ssh-keygen`` for generating Ed25519 key
pairs.  All actual cryptography is delegated to the system's OpenSSH tooling;
this module only handles argument construction, pre-flight checks, and error
reporting.
"""

import subprocess
from pathlib import Path


def generate_key(
    key_path: str,
    passphrase: str = "",
) -> tuple[bool, str]:
    """Generate an Ed25519 SSH key pair at *key_path*.

    Args:
        key_path:   Path to the private key file, e.g. ``~/.ssh/sshman_myserver``.
                    A tilde prefix is expanded.  The public key will be written
                    to ``<key_path>.pub`` automatically by ``ssh-keygen``.
        passphrase: Optional passphrase to protect the private key.  An empty
                    string generates a key with no passphrase.

    Returns:
        ``(True, "")`` on success, or ``(False, error_message)`` on failure.
        The error message is human-readable and suitable for display in the UI.
    """
    expanded = Path(key_path).expanduser()

    if expanded.exists():
        return False, f"File already exists: {expanded}"

    # Ensure the parent directory exists (typically ~/.ssh/)
    try:
        expanded.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Could not create directory {expanded.parent}: {exc}"

    cmd = [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-f",
        str(expanded),
        "-N",
        passphrase,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, ""
        # Prefer stderr; fall back to stdout if stderr is empty
        error_detail = result.stderr.strip() or result.stdout.strip()
        return False, error_detail or f"ssh-keygen exited with code {result.returncode}"
    except FileNotFoundError:
        return False, "ssh-keygen not found on PATH"
