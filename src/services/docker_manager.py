"""Docker container management service for SCAR."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docker
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError

from ..utils.project_config import ProjectConfig, get_project_config


logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for managed projects."""

    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        """
        Initialize Docker manager.

        Args:
            socket_path: Path to Docker socket
        """
        self.socket_path = socket_path
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            try:
                self._client = docker.DockerClient(base_url=f"unix://{self.socket_path}")
                # Test connection
                self._client.ping()
            except DockerException as e:
                logger.error(f"Failed to connect to Docker: {e}")
                raise
        return self._client

    async def get_container_status(
        self, project_name: str
    ) -> Dict[str, Dict[str, str | bool]]:
        """
        Get status of all containers for a project.

        Args:
            project_name: Name of the project

        Returns:
            Dictionary mapping container names to their status info

        Raises:
            ValueError: If project config not found
            DockerException: If Docker operation fails
        """
        config = get_project_config(project_name)
        if not config:
            raise ValueError(f"Project '{project_name}' not found in configuration")

        return await asyncio.to_thread(self._get_container_status_sync, config)

    def _get_container_status_sync(
        self, config: ProjectConfig
    ) -> Dict[str, Dict[str, str | bool]]:
        """Synchronous version of get_container_status."""
        statuses = {}

        for container_name in config.containers:
            try:
                container = self.client.containers.get(container_name)
                info = container.attrs

                # Parse uptime
                started_at = info["State"]["StartedAt"]
                uptime = self._calculate_uptime(started_at)

                # Get port mappings
                ports = self._format_ports(info.get("NetworkSettings", {}).get("Ports", {}))

                statuses[container_name] = {
                    "running": info["State"]["Running"],
                    "status": info["State"]["Status"],
                    "health": info["State"].get("Health", {}).get("Status", "unknown"),
                    "uptime": uptime,
                    "started_at": started_at,
                    "ports": ports,
                    "image": info["Config"]["Image"],
                    "is_primary": container_name == config.primary_container,
                }

            except NotFound:
                statuses[container_name] = {
                    "running": False,
                    "status": "not_found",
                    "health": "unknown",
                    "uptime": "N/A",
                    "started_at": None,
                    "ports": "",
                    "image": "unknown",
                    "is_primary": container_name == config.primary_container,
                }
            except Exception as e:
                logger.error(f"Error getting status for {container_name}: {e}")
                statuses[container_name] = {
                    "running": False,
                    "status": f"error: {str(e)}",
                    "health": "unknown",
                    "uptime": "N/A",
                    "started_at": None,
                    "ports": "",
                    "image": "unknown",
                    "is_primary": container_name == config.primary_container,
                }

        return statuses

    async def get_container_logs(
        self, project_name: str, lines: int = 50, container_name: Optional[str] = None
    ) -> str:
        """
        Get logs from a project's container.

        Args:
            project_name: Name of the project
            lines: Number of log lines to retrieve
            container_name: Specific container name. If None, uses primary container

        Returns:
            Container logs as string

        Raises:
            ValueError: If project config not found
            DockerException: If Docker operation fails
        """
        config = get_project_config(project_name)
        if not config:
            raise ValueError(f"Project '{project_name}' not found in configuration")

        target_container = container_name or config.primary_container

        return await asyncio.to_thread(self._get_container_logs_sync, target_container, lines)

    def _get_container_logs_sync(self, container_name: str, lines: int) -> str:
        """Synchronous version of get_container_logs."""
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(
                stdout=True, stderr=True, tail=lines, timestamps=True
            ).decode("utf-8", errors="replace")
            return logs
        except NotFound:
            return f"Container '{container_name}' not found"
        except Exception as e:
            logger.error(f"Error getting logs for {container_name}: {e}")
            return f"Error retrieving logs: {str(e)}"

    async def restart_containers(self, project_name: str) -> Dict[str, bool]:
        """
        Restart all containers for a project.

        Args:
            project_name: Name of the project

        Returns:
            Dictionary mapping container names to success status

        Raises:
            ValueError: If project config not found
        """
        config = get_project_config(project_name)
        if not config:
            raise ValueError(f"Project '{project_name}' not found in configuration")

        return await asyncio.to_thread(self._restart_containers_sync, config)

    def _restart_containers_sync(self, config: ProjectConfig) -> Dict[str, bool]:
        """Synchronous version of restart_containers."""
        results = {}

        for container_name in config.containers:
            try:
                container = self.client.containers.get(container_name)
                container.restart(timeout=10)
                results[container_name] = True
                logger.info(f"Restarted container: {container_name}")
            except Exception as e:
                logger.error(f"Failed to restart {container_name}: {e}")
                results[container_name] = False

        return results

    async def deploy_project(self, project_name: str) -> Tuple[bool, str]:
        """
        Deploy workspace changes to production.

        This performs:
        1. Sync workspace → production directory
        2. Rebuild Docker images (if needed)
        3. Restart containers

        Args:
            project_name: Name of the project

        Returns:
            Tuple of (success, message)

        Raises:
            ValueError: If project config not found
        """
        config = get_project_config(project_name)
        if not config:
            raise ValueError(f"Project '{project_name}' not found in configuration")

        return await asyncio.to_thread(self._deploy_project_sync, config)

    def _deploy_project_sync(self, config: ProjectConfig) -> Tuple[bool, str]:
        """Synchronous version of deploy_project."""
        workspace = Path(config.workspace)
        production = Path(config.production)

        if not workspace.exists():
            return False, f"Workspace directory not found: {workspace}"

        # Create production directory if it doesn't exist
        production.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Sync files
            import subprocess

            rsync_result = subprocess.run(
                [
                    "rsync",
                    "-av",
                    "--exclude",
                    ".git",
                    "--exclude",
                    "__pycache__",
                    "--exclude",
                    "*.pyc",
                    f"{workspace}/",
                    f"{production}/",
                ],
                capture_output=True,
                text=True,
            )

            if rsync_result.returncode != 0:
                return False, f"File sync failed: {rsync_result.stderr}"

            # Step 2: Check if we need to rebuild
            dockerfile_changed = "Dockerfile" in rsync_result.stdout
            requirements_changed = "requirements.txt" in rsync_result.stdout or "pyproject.toml" in rsync_result.stdout

            if dockerfile_changed or requirements_changed:
                logger.info("Rebuilding Docker images due to dependency changes")
                build_result = subprocess.run(
                    ["docker", "compose", "build"],
                    cwd=production,
                    capture_output=True,
                    text=True,
                )

                if build_result.returncode != 0:
                    return False, f"Docker build failed: {build_result.stderr}"

            # Step 3: Restart containers
            restart_result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=production,
                capture_output=True,
                text=True,
            )

            if restart_result.returncode != 0:
                return False, f"Container restart failed: {restart_result.stderr}"

            return True, "Deployment successful"

        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return False, f"Deployment error: {str(e)}"

    @staticmethod
    def _calculate_uptime(started_at: str) -> str:
        """Calculate human-readable uptime from start timestamp."""
        try:
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - start_time

            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except Exception:
            return "unknown"

    @staticmethod
    def _format_ports(ports: Dict) -> str:
        """Format port mappings for display."""
        if not ports:
            return ""

        port_strs = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get("HostPort", "?")
                    port_strs.append(f"{host_port}→{container_port}")

        return ", ".join(port_strs) if port_strs else ""

    def close(self):
        """Close Docker client connection."""
        if self._client:
            self._client.close()
            self._client = None
