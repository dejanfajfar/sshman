"""Tests for Docker container discovery functionality."""

from unittest.mock import MagicMock, patch

from sshman.docker import (
    detect_shell,
    get_running_containers,
    is_docker_available,
)
from sshman.models import DockerContainer


class TestIsDockerAvailable:
    """Tests for is_docker_available function."""

    def test_returns_true_when_docker_running(self) -> None:
        """Test that True is returned when Docker daemon is responsive."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_docker_available() is True
            mock_run.assert_called_once()

    def test_returns_false_when_docker_not_running(self) -> None:
        """Test that False is returned when Docker daemon is not running."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert is_docker_available() is False

    def test_returns_false_when_docker_not_installed(self) -> None:
        """Test that False is returned when Docker is not installed."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert is_docker_available() is False

    def test_returns_false_on_timeout(self) -> None:
        """Test that False is returned when Docker command times out."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=5)
            assert is_docker_available() is False


class TestGetRunningContainers:
    """Tests for get_running_containers function."""

    def test_parses_single_container(self) -> None:
        """Test parsing of a single container from docker ps output."""
        docker_output = '{"ID":"abc123def456","Names":"my-nginx","Image":"nginx:latest","Status":"Up 2 hours"}\n'

        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=docker_output,
            )
            containers = get_running_containers()

            assert len(containers) == 1
            assert containers[0].container_id == "abc123def456"
            assert containers[0].name == "my-nginx"
            assert containers[0].image == "nginx:latest"
            assert containers[0].status == "Up 2 hours"

    def test_parses_multiple_containers(self) -> None:
        """Test parsing of multiple containers from docker ps output."""
        docker_output = (
            '{"ID":"abc123","Names":"nginx","Image":"nginx:latest","Status":"Up 2 hours"}\n'
            '{"ID":"def456","Names":"redis","Image":"redis:7","Status":"Up 5 minutes"}\n'
            '{"ID":"ghi789","Names":"postgres","Image":"postgres:16","Status":"Up 1 hour"}\n'
        )

        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=docker_output,
            )
            containers = get_running_containers()

            assert len(containers) == 3
            assert containers[0].name == "nginx"
            assert containers[1].name == "redis"
            assert containers[2].name == "postgres"

    def test_returns_empty_list_when_no_containers(self) -> None:
        """Test empty list when no containers are running."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
            )
            containers = get_running_containers()
            assert containers == []

    def test_returns_empty_list_on_docker_error(self) -> None:
        """Test empty list when docker ps fails."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            containers = get_running_containers()
            assert containers == []

    def test_returns_empty_list_when_docker_not_available(self) -> None:
        """Test empty list when Docker is not installed."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            containers = get_running_containers()
            assert containers == []

    def test_skips_malformed_json_lines(self) -> None:
        """Test that malformed JSON lines are skipped."""
        docker_output = (
            '{"ID":"abc123","Names":"nginx","Image":"nginx:latest","Status":"Up 2 hours"}\n'
            "not valid json\n"
            '{"ID":"def456","Names":"redis","Image":"redis:7","Status":"Up 5 minutes"}\n'
        )

        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=docker_output,
            )
            containers = get_running_containers()

            assert len(containers) == 2
            assert containers[0].name == "nginx"
            assert containers[1].name == "redis"


class TestDetectShell:
    """Tests for detect_shell function."""

    def test_returns_bash_when_available(self) -> None:
        """Test that /bin/bash is returned when bash exists in container."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            shell = detect_shell("my-container")
            assert shell == "/bin/bash"

    def test_returns_sh_when_bash_not_available(self) -> None:
        """Test that /bin/sh is returned when bash doesn't exist."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            shell = detect_shell("my-container")
            assert shell == "/bin/sh"

    def test_returns_sh_on_error(self) -> None:
        """Test that /bin/sh is returned on any error."""
        with patch("sshman.docker.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Connection error")
            shell = detect_shell("my-container")
            assert shell == "/bin/sh"


class TestDockerContainerModel:
    """Tests for DockerContainer model."""

    def test_exec_command_default_shell(self) -> None:
        """Test exec_command with default shell."""
        container = DockerContainer(
            container_id="abc123",
            name="my-nginx",
            image="nginx:latest",
            status="Up 2 hours",
        )
        cmd = container.exec_command()
        assert cmd == ["docker", "exec", "-it", "my-nginx", "/bin/sh"]

    def test_exec_command_custom_shell(self) -> None:
        """Test exec_command with custom shell."""
        container = DockerContainer(
            container_id="abc123",
            name="my-nginx",
            image="nginx:latest",
            status="Up 2 hours",
        )
        cmd = container.exec_command("/bin/bash")
        assert cmd == ["docker", "exec", "-it", "my-nginx", "/bin/bash"]

    def test_display_target(self) -> None:
        """Test display_target returns image name."""
        container = DockerContainer(
            container_id="abc123",
            name="my-nginx",
            image="nginx:1.25-alpine",
            status="Up 2 hours",
        )
        assert container.display_target() == "nginx:1.25-alpine"
