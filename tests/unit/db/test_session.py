from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import build_engine, build_session_factory, get_session

MEMORY_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = build_engine(MEMORY_URL)
    yield engine
    await engine.dispose()


async def test_get_session_when_sqlite_memory_executes_select(engine: AsyncEngine) -> None:
    factory = build_session_factory(engine)

    async for session in get_session(factory):
        result = await session.execute(text("SELECT 1"))

        assert result.scalar_one() == 1


async def test_build_engine_when_sqlite_enables_foreign_keys(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("PRAGMA foreign_keys"))

        assert result.scalar_one() == 1
