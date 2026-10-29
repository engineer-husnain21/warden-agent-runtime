"""Dependency wiring. Concrete classes are built here and injected with FastAPI `Depends`."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import build_engine, build_session_factory, get_session


@lru_cache
def get_engine() -> AsyncEngine:
    return build_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return build_session_factory(get_engine())


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session(get_session_factory()):
        yield session
