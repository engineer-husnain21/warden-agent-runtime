from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from mcp_servers.warehouse.seed import seed_warehouse
from mcp_servers.warehouse.server import create_server
from mcp_servers.warehouse.warehouse_store import WarehouseStore

ORDERS_CSV = Path(__file__).resolve().parents[4] / "data" / "orders.csv"


@pytest.fixture
def server(tmp_path: Path) -> MCPServer:
    db_path = tmp_path / "warehouse.db"
    seed_warehouse(ORDERS_CSV, db_path, now=datetime(2026, 10, 30, 12, 0, tzinfo=UTC))
    return create_server(WarehouseStore(db_path))


async def test_list_tools_when_server_created_exposes_read_tools(server: MCPServer) -> None:
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools.tools} == {"list_tables", "describe_table", "run_query"}


async def test_list_tables_when_called_returns_orders(server: MCPServer) -> None:
    async with Client(server) as client:
        result = await client.call_tool("list_tables", {})

    assert result.structured_content == {"tables": ["orders"]}


async def test_describe_table_when_unknown_table_returns_error(server: MCPServer) -> None:
    async with Client(server) as client:
        result = await client.call_tool("describe_table", {"table": "customers"})

    assert result.is_error


async def test_run_query_when_select_returns_rows(server: MCPServer) -> None:
    sql = (
        "SELECT failure_reason, COUNT(*) AS failures FROM orders "
        "WHERE status = 'failed' AND created_at >= datetime('2026-10-30 12:00:00', '-1 day') "
        "GROUP BY failure_reason ORDER BY failures DESC LIMIT 3"
    )
    async with Client(server) as client:
        result = await client.call_tool("run_query", {"sql": sql})

    assert not result.is_error
    assert result.structured_content is not None
    rows = result.structured_content["rows"]
    assert [row["failure_reason"] for row in rows] == [
        "payment_timeout",
        "inventory_unavailable",
        "card_declined",
    ]
