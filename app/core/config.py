from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """All runtime settings, read from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: LogLevel = "INFO"
    database_url: str = "sqlite+aiosqlite:///./warden.db"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
