from pydantic_settings import BaseSettings, SettingsConfigDict


class ConsoleSettings(BaseSettings):
    """Where the console finds the API, read from `WARDEN_CONSOLE_*` env vars and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="WARDEN_CONSOLE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_url: str = "http://127.0.0.1:8000"
    api_key: str = ""
    timeout_seconds: float = 30.0
