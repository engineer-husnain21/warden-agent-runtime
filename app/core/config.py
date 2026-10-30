from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.caller import Caller

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LlmProvider = Literal["groq", "gemini"]


class Settings(BaseSettings):
    """All runtime settings, read from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: LogLevel = "INFO"
    database_url: str = "sqlite+aiosqlite:///./warden.db"

    # Auth: API key -> caller identity and role. Paths listed here need no key.
    api_keys: dict[str, Caller] = {}
    auth_exempt_paths: list[str] = ["/api/v1/health", "/docs", "/openapi.json"]

    # LLM: switching provider needs only LLM_PROVIDER (plus that provider's key).
    llm_provider: LlmProvider = "groq"
    llm_timeout_seconds: float = 60.0
    llm_max_attempts: int = 4

    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_input_price_per_mtok: float = 0.15
    groq_output_price_per_mtok: float = 0.60

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_input_price_per_mtok: float = 0.30
    gemini_output_price_per_mtok: float = 2.50

    # MCP: server name -> Python module started as `python -m <module>` over stdio.
    mcp_server_modules: dict[str, str] = {
        "warehouse": "mcp_servers.warehouse.server",
        "github": "mcp_servers.github.server",
        "notifier": "mcp_servers.notifier.server",
    }
    mcp_tool_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
