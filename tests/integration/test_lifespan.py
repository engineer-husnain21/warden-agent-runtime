from collections.abc import Iterator
from pathlib import Path

import pytest

import app.main as main_module
from app.clients.mcp_tool_client import McpToolClient
from app.core.dependencies import get_engine, get_http_client, get_tool_client
from app.repositories.checkpoint_repository import CheckpointRepository
from tests.fakes.fake_tool_client import FakeToolClient


class _FakeRunService:
    def __init__(self) -> None:
        self.resume_calls = 0

    async def resume_interrupted_runs(self) -> int:
        self.resume_calls += 1
        return 0


@pytest.fixture(autouse=True)
def _fresh_shared_clients() -> Iterator[None]:
    """The lifespan closes the cached HTTP client and engine; never leak those to other tests."""
    yield
    for cached in (get_engine, get_http_client, get_tool_client):
        cached.cache_clear()


async def test_lifespan_when_app_starts_connects_tools_and_resumes_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tools, runs = FakeToolClient(), _FakeRunService()
    checkpoints = CheckpointRepository(f"sqlite+aiosqlite:///{(tmp_path / 'cp.db').as_posix()}")
    monkeypatch.setattr(main_module, "get_tool_client", lambda: tools)
    monkeypatch.setattr(main_module, "get_checkpoint_repository", lambda: checkpoints)
    monkeypatch.setattr(main_module, "get_agent_run_service", lambda: runs)
    app = main_module.create_app()

    async with main_module.lifespan(app):
        assert tools.connected
        assert checkpoints.saver is not None
        assert runs.resume_calls == 1

    assert not tools.connected


def test_get_tool_client_when_default_settings_returns_mcp_client() -> None:
    get_tool_client.cache_clear()

    assert isinstance(get_tool_client(), McpToolClient)
