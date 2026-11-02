from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base
from app.db.session import build_engine, build_session_factory


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session on a fresh in-memory SQLite database with all tables created."""
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with build_session_factory(engine)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def session_factory(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A session factory on a fresh SQLite file, for services that open their own sessions."""
    engine = build_engine(f"sqlite+aiosqlite:///{(tmp_path / 'warden.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield build_session_factory(engine)
    await engine.dispose()
