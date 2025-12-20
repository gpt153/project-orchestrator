"""
Configuration management using Pydantic Settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Project Orchestrator"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/project_orchestrator"

    # Frontend
    frontend_url: str = "http://localhost:5173"  # Vite dev server
    serve_frontend: bool = False  # Set to True in production

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # GitHub (optional for MVP)
    github_token: Optional[str] = None
    github_webhook_secret: Optional[str] = None

    # Telegram (optional for MVP)
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None


# Global settings instance
settings = Settings()
