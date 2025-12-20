"""Project configuration loader for managing Docker projects."""

import json
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Configuration for a managed project."""

    workspace: str = Field(..., description="Path to workspace directory")
    production: str = Field(..., description="Path to production directory")
    compose_project: str = Field(..., description="Docker Compose project name")
    containers: list[str] = Field(..., description="List of container names")
    primary_container: str = Field(..., description="Primary container name")
    auto_detect: bool = Field(
        default=False, description="Auto-detect containers from docker-compose.yml"
    )


# Global cache for project configurations
_project_configs: Optional[Dict[str, ProjectConfig]] = None
_config_file_path = Path("/workspace/.scar-projects.json")


def load_project_config(config_path: Optional[Path] = None) -> Dict[str, ProjectConfig]:
    """
    Load project configurations from JSON file.

    Args:
        config_path: Path to config file. Defaults to /workspace/.scar-projects.json

    Returns:
        Dictionary mapping project names to ProjectConfig objects

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    global _project_configs

    path = config_path or _config_file_path

    if not path.exists():
        raise FileNotFoundError(f"Project config file not found: {path}")

    try:
        with open(path, "r") as f:
            data = json.load(f)

        configs = {}
        for project_name, config_data in data.items():
            configs[project_name] = ProjectConfig(**config_data)

        _project_configs = configs
        return configs

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Error loading project config: {e}")


def get_project_config(project_name: str) -> Optional[ProjectConfig]:
    """
    Get configuration for a specific project.

    Args:
        project_name: Name of the project (e.g., "project-orchestrator")

    Returns:
        ProjectConfig if found, None otherwise

    Note:
        Automatically loads config from file on first call.
    """
    global _project_configs

    if _project_configs is None:
        try:
            load_project_config()
        except FileNotFoundError:
            return None

    return _project_configs.get(project_name) if _project_configs else None


def reload_project_config() -> Dict[str, ProjectConfig]:
    """
    Force reload of project configurations from disk.

    Returns:
        Dictionary of project configurations

    Useful when config file has been modified.
    """
    global _project_configs
    _project_configs = None
    return load_project_config()
