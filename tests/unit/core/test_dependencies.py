from collections.abc import Iterator

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dependencies import get_db_session, get_engine, get_session_factory


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture(autouse=True)
def _memory_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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
