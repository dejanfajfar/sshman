"""Data models for SSH connections."""

import sys
from datetime import datetime

from pydantic import BaseModel, Field


class Connection(BaseModel):
    """Represents an SSH connection configuration."""

    name: str = Field(..., description="Display name / alias for the connection")
    hostname: str = Field(..., description="Hostname or IP address")
    user: str | None = Field(default=None, description="SSH username")
    port: int = Field(default=22, ge=1, le=65535, description="SSH port")
    identity_file: str | None = Field(
        default=None, description="Path to private key file"
    )
    description: str | None = Field(
        default=None, description="Optional description or notes"
    )
    auto_add_key: bool = Field(
        default=False,
        description="Automatically add identity_file to ssh-agent before connecting",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for grouping related connections",
    )

    def ssh_add_command(self) -> list[str] | None:
        """Build the ssh-add command to load the identity key into the agent.

        Returns None if auto_add_key is False or no identity_file is set.
        On macOS, --apple-use-keychain is included so the passphrase is stored
        in the macOS Keychain and survives reboots.
        """
        if not self.auto_add_key or not self.identity_file:
            return None

        cmd = ["ssh-add"]
        if sys.platform == "darwin":
            cmd.append("--apple-use-keychain")
        cmd.append(self.identity_file)
        return cmd

    def ssh_command(self) -> list[str]:
        """Build the SSH command arguments for this connection."""
        cmd = ["ssh"]

        # Add connection timeout to fail fast on unreachable hosts
        cmd.extend(["-o", "ConnectTimeout=10"])
        # Detect dead connections
        cmd.extend(["-o", "ServerAliveInterval=5"])
        cmd.extend(["-o", "ServerAliveCountMax=2"])

        if self.port != 22:
            cmd.extend(["-p", str(self.port)])

        if self.identity_file:
            cmd.extend(["-i", self.identity_file])

        if self.user:
            cmd.append(f"{self.user}@{self.hostname}")
        else:
            cmd.append(self.hostname)

        return cmd

    def display_target(self) -> str:
        """Return a display string like 'user@hostname:port'."""
        target = ""
        if self.user:
            target = f"{self.user}@"
        target += self.hostname
        if self.port != 22:
            target += f":{self.port}"
        return target


class DockerContainer(BaseModel):
    """Represents a running Docker container."""

    container_id: str = Field(..., description="Container ID (short, 12 chars)")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image name with tag")
    status: str = Field(..., description="Container status (e.g., 'Up 2 hours')")

    def exec_command(self, shell: str = "/bin/sh") -> list[str]:
        """Build docker exec command for this container.

        Args:
            shell: The shell to use inside the container.

        Returns:
            Command list like ["docker", "exec", "-it", "container", "/bin/sh"].
        """
        return ["docker", "exec", "-it", self.name, shell]

    def display_target(self) -> str:
        """Return the image name for display."""
        return self.image


class AppConfig(BaseModel):
    """Application configuration stored in connections.json."""

    version: str = Field(default="1.0", description="Config file version")
    connections: list[Connection] = Field(
        default_factory=list, description="List of saved connections"
    )


class HistoryEntry(BaseModel):
    """Represents a connection history entry."""

    connection_name: str = Field(..., description="Name of the connection")
    connection_target: str = Field(..., description="Target (user@host:port)")
    connection_type: str = Field(default="ssh", description="Type: 'ssh' or 'docker'")
    started_at: datetime = Field(..., description="When connection was initiated")
    ended_at: datetime | None = Field(default=None, description="When connection ended")
    duration_seconds: float | None = Field(
        default=None, description="Session duration in seconds"
    )
    exit_code: int | None = Field(default=None, description="Process exit code")
    success: bool = Field(
        default=False, description="Whether connection was successful"
    )
    error_message: str | None = Field(
        default=None, description="Error details if failed"
    )

    def format_duration(self) -> str:
        """Format duration as HH:MM:SS or '-' if not available."""
        if self.duration_seconds is None:
            return "-"
        total_seconds = int(self.duration_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def format_started_at(self) -> str:
        """Format start time for display."""
        return self.started_at.strftime("%b %d, %H:%M")

    def format_status(self) -> str:
        """Format status for display."""
        if self.success:
            return "✓"
        if self.exit_code is not None:
            return f"✗ ({self.exit_code})"
        return "✗"


class HistoryConfig(BaseModel):
    """History stored in history.json."""

    version: str = Field(default="1.0", description="History file version")
    entries: list[HistoryEntry] = Field(
        default_factory=list, description="List of history entries"
    )
