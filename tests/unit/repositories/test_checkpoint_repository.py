from pathlib import Path
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.exceptions import ConfigurationError
from app.repositories.checkpoint_repository import CheckpointRepository


class _State(TypedDict):
    count: int


async def _increment(state: _State) -> dict[str, Any]:
    return {"count": state["count"] + 1}


def _graph(saver: BaseCheckpointSaver[str]) -> CompiledStateGraph[Any, Any, Any, Any]:
    builder = StateGraph(_State)
    builder.add_node("increment", _increment)
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    return builder.compile(checkpointer=saver)


async def test_get_saver_when_sqlite_url_persists_and_reloads_checkpoint(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{(tmp_path / 'checkpoints.db').as_posix()}"
    config: Any = {"configurable": {"thread_id": "run-1"}}

    first = CheckpointRepository(url)
    await _graph(await first.open()).ainvoke({"count": 41}, config)
    await first.close()

    second = CheckpointRepository(url)
    state = await _graph(await second.open()).aget_state(config)
    await second.close()

    assert state.values == {"count": 42}


def test_init_when_url_not_sqlite_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="CHECKPOINT_DATABASE_URL"):
        CheckpointRepository("postgresql+asyncpg://localhost/warden")


def test_saver_when_not_open_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        _ = CheckpointRepository("sqlite+aiosqlite:///:memory:").saver
