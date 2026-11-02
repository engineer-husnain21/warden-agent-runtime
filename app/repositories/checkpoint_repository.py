from contextlib import AsyncExitStack

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.exceptions import ConfigurationError

_SQLITE_PREFIXES = ("sqlite+aiosqlite:///", "sqlite:///")


class CheckpointRepository:
    """Owns the LangGraph checkpoint saver that makes runs durable.

    `open()` once at startup, `close()` at shutdown. The orchestrator only receives the saver;
    it never opens connections itself. Checkpoints live in their own SQLite file, so they do
    not compete with the app database for SQLite's single writer lock.
    """

    def __init__(self, database_url: str) -> None:
        self._path = _sqlite_path(database_url)
        self._stack: AsyncExitStack | None = None
        self._saver: AsyncSqliteSaver | None = None

    async def open(self) -> BaseCheckpointSaver[str]:
        if self._saver is None:
            stack = AsyncExitStack()
            saver = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(self._path))
            await saver.setup()
            self._stack, self._saver = stack, saver
        return self._saver

    @property
    def saver(self) -> BaseCheckpointSaver[str]:
        if self._saver is None:
            raise ConfigurationError("CheckpointRepository is not open")
        return self._saver

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack, self._saver = None, None


def _sqlite_path(database_url: str) -> str:
    for prefix in _SQLITE_PREFIXES:
        if database_url.startswith(prefix):
            return database_url.removeprefix(prefix)
    raise ConfigurationError(
        "CHECKPOINT_DATABASE_URL must be a SQLite URL "
        "(PostgreSQL would need langgraph-checkpoint-postgres)",
        details={"setting": "CHECKPOINT_DATABASE_URL"},
    )
