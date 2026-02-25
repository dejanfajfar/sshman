"""SSH config file parser for importing existing connections."""

import contextlib
import re
from pathlib import Path

from .models import Connection


def get_ssh_config_path() -> Path:
    """Get the path to the user's SSH config file."""
    return Path.home() / ".ssh" / "config"


def parse_ssh_config() -> list[Connection]:
    """
    Parse ~/.ssh/config and return a list of Connection objects.

    This is a simple parser that handles the most common directives.
    """
    config_path = get_ssh_config_path()

    if not config_path.exists():
        return []

    connections: list[Connection] = []
    current_host: dict[str, str] = {}

    try:
        content = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    for line in content.splitlines():
        # Remove comments and strip whitespace
        line = re.sub(r"#.*$", "", line).strip()

        if not line:
            continue

        # Parse key-value pairs (handles both "Key Value" and "Key=Value")
        match = re.match(r"^(\w+)\s*[=\s]\s*(.+)$", line, re.IGNORECASE)
        if not match:
            continue

        key = match.group(1).lower()
        value = match.group(2).strip()

        if key == "host":
            # Save previous host if exists
            if current_host and "host" in current_host:
                conn = _dict_to_connection(current_host)
                if conn:
                    connections.append(conn)

            # Start new host block
            current_host = {"host": value}
        else:
            # Add directive to current host
            current_host[key] = value

    # Don't forget the last host
    if current_host and "host" in current_host:
        conn = _dict_to_connection(current_host)
        if conn:
            connections.append(conn)

    return connections


def _dict_to_connection(data: dict[str, str]) -> Connection | None:
    """Convert a parsed host dict to a Connection object."""
    host = data.get("host", "")

    # Skip wildcard patterns and empty hosts
    if not host or "*" in host or "?" in host:
        return None

    # Get hostname (fallback to host alias if not specified)
    hostname = data.get("hostname", host)

    # Parse port
    port = 22
    if "port" in data:
        with contextlib.suppress(ValueError):
            port = int(data["port"])

    # Expand ~ in identity file path
    identity_file = data.get("identityfile")
    if identity_file and identity_file.startswith("~"):
        identity_file = str(Path(identity_file).expanduser())

    return Connection(
        name=host,
        hostname=hostname,
        user=data.get("user"),
        port=port,
        identity_file=identity_file,
    )
