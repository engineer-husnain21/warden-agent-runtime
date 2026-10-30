import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings

ENV_VARS = ("APP_ENV", "LOG_LEVEL", "DATABASE_URL")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_settings_when_env_missing_uses_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite+aiosqlite:///./warden.db"


def test_settings_when_env_set_reads_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.log_level == "DEBUG"
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"


def test_settings_when_log_level_invalid_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_when_api_key_set_hides_it_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-value")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.groq_api_key is not None
    assert settings.groq_api_key.get_secret_value() == "super-secret-value"
    assert "super-secret-value" not in repr(settings)


def test_settings_when_api_keys_json_set_parses_callers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEYS", '{"k1": {"name": "ada", "role": "admin"}}')

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.api_keys["k1"].name == "ada"
    assert settings.api_keys["k1"].role.value == "admin"


def test_get_settings_when_called_twice_returns_same_instance() -> None:
    assert get_settings() is get_settings()
