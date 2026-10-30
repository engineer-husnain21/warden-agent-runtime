from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class NotifierSettings(BaseSettings):
    """Settings for the notifier server, read from `NOTIFIER_*` env vars and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="NOTIFIER_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    db_path: Path = Path("data/notifier.db")
