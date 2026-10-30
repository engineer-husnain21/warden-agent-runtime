from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_servers.warehouse.seed import seed_warehouse
from mcp_servers.warehouse.warehouse_store import WarehouseStore

ORDERS_CSV = Path(__file__).resolve().parents[4] / "data" / "orders.csv"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "warehouse.db"
    seed_warehouse(ORDERS_CSV, path, now=datetime(2026, 10, 30, 12, 0, tzinfo=UTC))
    return path


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET status = 'completed'",
        "DROP TABLE orders",
        "INSERT INTO orders (order_id) VALUES (1)",
        "PRAGMA table_info(orders)",
        "ATTACH DATABASE 'x.db' AS x",
    ],
)
def test_run_query_when_not_a_select_raises_error(db_path: Path, sql: str) -> None:
    with pytest.raises(ToolError):
        WarehouseStore(db_path).run_query(sql)


def test_run_query_when_two_statements_raises_error(db_path: Path) -> None:
    with pytest.raises(ToolError, match="one SQL statement"):
        WarehouseStore(db_path).run_query("SELECT 1; DELETE FROM orders")


def test_run_query_when_write_hidden_in_cte_is_denied(db_path: Path) -> None:
    with pytest.raises(ToolError):
        WarehouseStore(db_path).run_query(
            "WITH gone AS (SELECT 1) DELETE FROM orders WHERE order_id IN (SELECT * FROM gone)"
        )

    assert len(WarehouseStore(db_path).run_query("SELECT order_id FROM orders")[0]) == 200


def test_run_query_when_more_rows_than_cap_truncates(db_path: Path) -> None:
    rows, truncated = WarehouseStore(db_path, max_rows=10).run_query("SELECT * FROM orders")

    assert len(rows) == 10
    assert truncated


def test_run_query_when_trailing_semicolon_is_accepted(db_path: Path) -> None:
    rows, truncated = WarehouseStore(db_path).run_query("SELECT COUNT(*) AS n FROM orders;")

    assert rows == [{"n": 500}]
    assert not truncated
