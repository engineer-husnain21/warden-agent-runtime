"""Starts the three real MCP servers as subprocesses (no network, GitHub in dry-run)."""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from mcp import StdioServerParameters

from app.clients.mcp_tool_client import McpToolClient
from app.core.exceptions import ExternalServiceError
from app.schemas.tool_call import ToolCall
from mcp_servers.warehouse.seed import seed_warehouse

# One set of server processes for the whole module keeps this file fast.
pytestmark = pytest.mark.asyncio(loop_scope="module")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_MODULES = {
    "warehouse": "mcp_servers.warehouse.server",
    "github": "mcp_servers.github.server",
    "notifier": "mcp_servers.notifier.server",
}


def _params(module: str, env: dict[str, str]) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable, args=["-m", module], env=env, cwd=str(PROJECT_ROOT)
    )


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def tool_client(tmp_path_factory: pytest.TempPathFactory) -> AsyncIterator[McpToolClient]:
    tmp_path = tmp_path_factory.mktemp("mcp")
    warehouse_db = tmp_path / "warehouse.db"
    seed_warehouse(PROJECT_ROOT / "data" / "orders.csv", warehouse_db)
    env = {
        **os.environ,
        "WAREHOUSE_DB_PATH": str(warehouse_db),
        "NOTIFIER_DB_PATH": str(tmp_path / "notifier.db"),
        "GITHUB_MODE": "dry-run",
        "GITHUB_REPO": "octo/warden-sandbox",
    }
    client = McpToolClient(
        {name: _params(module, env) for name, module in SERVER_MODULES.items()},
        timeout_seconds=30,
    )
    await client.connect()
    yield client
    await client.close()


async def test_list_tools_when_servers_started_returns_all_three(
    tool_client: McpToolClient,
) -> None:
    names = {spec.name for spec in await tool_client.list_tools()}

    assert names == {
        "warehouse.list_tables",
        "warehouse.describe_table",
        "warehouse.run_query",
        "github.list_issues",
        "github.create_issue",
        "notifier.send_notification",
        "notifier.list_outbox",
    }


async def test_call_tool_when_select_returns_rows(tool_client: McpToolClient) -> None:
    result = await tool_client.call_tool(
        ToolCall(tool="warehouse.run_query", arguments={"sql": "SELECT COUNT(*) AS n FROM orders"})
    )

    assert result.ok
    assert result.content is not None
    assert result.content["rows"] == [{"n": 500}]
    assert result.latency_ms > 0


async def test_call_tool_when_github_dry_run_creates_fake_issue(
    tool_client: McpToolClient,
) -> None:
    result = await tool_client.call_tool(
        ToolCall(tool="github.create_issue", arguments={"title": "Payment timeouts"})
    )

    assert result.ok
    assert result.content is not None
    assert result.content["issue"]["dry_run"] is True


async def test_call_tool_when_write_sql_returns_not_ok(tool_client: McpToolClient) -> None:
    result = await tool_client.call_tool(
        ToolCall(tool="warehouse.run_query", arguments={"sql": "DELETE FROM orders"})
    )

    assert not result.ok
    assert result.error is not None
    assert "SELECT" in result.error


async def test_call_tool_when_server_unknown_returns_not_ok(tool_client: McpToolClient) -> None:
    result = await tool_client.call_tool(ToolCall(tool="email.send"))

    assert not result.ok
    assert result.error == "Unknown tool server: email"


async def test_connect_when_server_cannot_start_raises_external_service_error() -> None:
    client = McpToolClient(
        {"broken": _params("mcp_servers.does_not_exist", dict(os.environ))}, timeout_seconds=10
    )

    with pytest.raises(ExternalServiceError, match="broken"):
        await client.connect()
