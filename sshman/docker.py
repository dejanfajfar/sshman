"""Docker container discovery for sshman."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import DockerContainer


def is_docker_available() -> bool:
    """Check if Docker CLI is available and daemon is running.

    Returns:
        True if Docker is available and the daemon is responsive.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def get_running_containers() -> list[DockerContainer]:
    """Discover running Docker containers.

    Returns:
        List of DockerContainer objects for all running containers.
        Returns empty list if Docker is unavailable or on error.
    """
    # Import here to avoid circular imports
    from .models import DockerContainer

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        containers: list[DockerContainer] = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)
                container = DockerContainer(
                    container_id=data.get("ID", "")[:12],
                    name=data.get("Names", ""),
                    image=data.get("Image", ""),
                    status=data.get("Status", ""),
                )
                containers.append(container)
            except (json.JSONDecodeError, KeyError):
                # Skip malformed entries
                continue

        return containers

    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return []


def detect_shell(container_id: str) -> str:
    """Detect the best available shell in a container.

    Tries /bin/bash first, falls back to /bin/sh.

    Args:
        container_id: The container ID or name.

    Returns:
        Path to the shell executable.
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_id, "which", "bash"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return "/bin/bash"
    except Exception:
        pass

    return "/bin/sh"
