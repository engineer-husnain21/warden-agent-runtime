from collections.abc import Iterator

import pytest

import app.main as main_module
from app.clients.mcp_tool_client import McpToolClient
from app.core.dependencies import get_engine, get_http_client, get_tool_client
from tests.fakes.fake_tool_client import FakeToolClient


@pytest.fixture(autouse=True)
def _fresh_shared_clients() -> Iterator[None]:
    """The lifespan closes the cached HTTP client and engine; never leak those to other tests."""
    yield
    for cached in (get_engine, get_http_client, get_tool_client):
        cached.cache_clear()


async def test_lifespan_when_app_starts_connects_tool_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeToolClient()
    monkeypatch.setattr(main_module, "get_tool_client", lambda: fake)
    app = main_module.create_app()

    async with main_module.lifespan(app):
        assert fake.connected

    assert not fake.connected


def test_get_tool_client_when_default_settings_returns_mcp_client() -> None:
    get_tool_client.cache_clear()

    assert isinstance(get_tool_client(), McpToolClient)
