"""Data models for SSH connections."""

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

    def ssh_command(self) -> list[str]:
        """Build the SSH command arguments for this connection."""
        cmd = ["ssh"]

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


class AppConfig(BaseModel):
    """Application configuration stored in connections.json."""

    version: str = Field(default="1.0", description="Config file version")
    connections: list[Connection] = Field(
        default_factory=list, description="List of saved connections"
    )
