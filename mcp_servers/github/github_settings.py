from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubSettings(BaseSettings):
    """Settings for the GitHub server, read from `GITHUB_*` env vars and `.env`.

    `mode=dry-run` (default) never calls GitHub; `live` needs a token scoped to `repo` only.
    """

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mode: Literal["dry-run", "live"] = "dry-run"
    repo: str = "owner/warden-sandbox"
    token: SecretStr | None = None
    api_url: str = "https://api.github.com"
