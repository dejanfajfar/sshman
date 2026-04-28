"""SSH agent interaction helpers.

Provides utilities for checking whether an SSH agent is running and for
ensuring that a private key is loaded into it before a connection is made.
This avoids repeated passphrase prompts for the same key within a session.
"""

import os
import subprocess
import sys


def is_agent_running() -> bool:
    """Return True if an SSH agent is reachable via SSH_AUTH_SOCK."""
    return bool(os.environ.get("SSH_AUTH_SOCK"))


def is_key_loaded(identity_file: str) -> bool:
    """Return True if the given key is already present in the running agent.

    Runs ``ssh-add -l`` and compares the reported fingerprints against the
    fingerprint of *identity_file* obtained via ``ssh-keygen -lf``.  Returns
    False on any error so that the caller falls back to running ``ssh-add``.
    """
    try:
        list_result = subprocess.run(
            ["ssh-add", "-l"],
            capture_output=True,
            text=True,
        )
        # Exit code 1 means "agent has no identities", 2 means agent not running.
        if list_result.returncode not in (0, 1):
            return False

        loaded_fingerprints = list_result.stdout

        fingerprint_result = subprocess.run(
            ["ssh-keygen", "-lf", identity_file],
            capture_output=True,
            text=True,
        )
        if fingerprint_result.returncode != 0:
            return False

        # The fingerprint string is the second whitespace-separated token, e.g.:
        # 2048 SHA256:abc123... user@host (RSA)
        # We match on the whole fingerprint token to be safe.
        key_fp_line = fingerprint_result.stdout.strip()
        if not key_fp_line:
            return False

        tokens = key_fp_line.split()
        if len(tokens) < 2:
            return False

        fingerprint = tokens[1]
        return fingerprint in loaded_fingerprints

    except FileNotFoundError:
        # ssh-add or ssh-keygen not found on PATH
        return False


def ensure_key_in_agent(identity_file: str) -> tuple[bool, str]:
    """Ensure *identity_file* is loaded in the running SSH agent.

    1. If no agent is running, returns (False, error_message).
    2. If the key is already loaded, returns (True, "").
    3. Otherwise, runs ``ssh-add [--apple-use-keychain] <identity_file>``.
       Returns (True, "") on success or (False, error_message) on failure.

    On macOS the ``--apple-use-keychain`` flag is used so that a successfully
    entered passphrase is stored in the macOS Keychain and reused automatically
    on future invocations.
    """
    if not is_agent_running():
        return False, "No SSH agent found (SSH_AUTH_SOCK is not set)"

    if is_key_loaded(identity_file):
        return True, ""

    cmd = ["ssh-add"]
    if sys.platform == "darwin":
        cmd.append("--apple-use-keychain")
    cmd.append(identity_file)

    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            return True, ""
        return False, f"ssh-add exited with code {result.returncode}"
    except FileNotFoundError:
        return False, "ssh-add not found on PATH"
