from collections.abc import Iterator

import pytest
from sqlalchemy import text

from app.clients.gemini_llm_client import GeminiLlmClient
from app.clients.groq_llm_client import GroqLlmClient
from app.core.config import get_settings
from app.core.dependencies import (
    get_db_session,
    get_engine,
    get_http_client,
    get_llm_client,
    get_session_factory,
)
from app.core.exceptions import ConfigurationError


def _clear_caches() -> None:
    for cached in (get_settings, get_engine, get_session_factory, get_http_client, get_llm_client):
        cached.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    _clear_caches()
    yield
    _clear_caches()


async def test_get_db_session_when_called_yields_working_session() -> None:
    async for session in get_db_session():
        result = await session.execute(text("SELECT 1"))

        assert result.scalar_one() == 1
    await get_engine().dispose()


def test_get_session_factory_when_called_twice_returns_same_instance() -> None:
    assert get_session_factory() is get_session_factory()


def test_get_llm_client_when_provider_groq_returns_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "dummy-groq-key")

    assert isinstance(get_llm_client(), GroqLlmClient)


def test_get_llm_client_when_provider_gemini_returns_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key")

    assert isinstance(get_llm_client(), GeminiLlmClient)


def test_get_llm_client_when_key_missing_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")

    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        get_llm_client()
