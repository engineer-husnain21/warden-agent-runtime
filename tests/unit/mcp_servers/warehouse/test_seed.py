import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from mcp_servers.warehouse.seed import seed_warehouse

ORDERS_CSV = Path(__file__).resolve().parents[4] / "data" / "orders.csv"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _count(db_path: Path, where: str = "1 = 1") -> int:
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM orders WHERE {where}").fetchone()
    return int(row[0])


def test_seed_when_run_twice_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "warehouse.db"

    seed_warehouse(ORDERS_CSV, db_path, now=NOW)
    count = seed_warehouse(ORDERS_CSV, db_path, now=NOW)

    assert count == 500
    assert _count(db_path) == 500


def test_seed_when_run_turns_hours_ago_into_recent_timestamps(tmp_path: Path) -> None:
    db_path = tmp_path / "warehouse.db"

    seed_warehouse(ORDERS_CSV, db_path, now=NOW)

    recent_failed = _count(
        db_path, "status = 'failed' AND created_at >= datetime('2026-10-30 12:00:00', '-1 day')"
    )
    assert recent_failed == 35
    assert _count(db_path, "status != 'failed' AND failure_reason IS NOT NULL") == 0
