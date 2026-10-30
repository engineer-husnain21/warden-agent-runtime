"""Build the warehouse SQLite database from data/orders.csv.

Run: `uv run python -m mcp_servers.warehouse.seed`. Safe to run again: the table is rebuilt.
"""

import csv
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mcp_servers.warehouse.warehouse_settings import WarehouseSettings

# SQLite's own datetime format, so queries like `created_at >= datetime('now', '-1 day')` work.
SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

_CREATE_ORDERS = """
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    status TEXT NOT NULL,
    failure_reason TEXT,
    payment_provider TEXT NOT NULL,
    region TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""
_INSERT_ORDER = "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

logger = logging.getLogger(__name__)


def seed_warehouse(csv_path: Path, db_path: Path, now: datetime | None = None) -> int:
    """(Re)create the `orders` table; `hours_ago` in the CSV becomes a UTC `created_at`."""
    now = now or datetime.now(UTC)
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = [
            (
                int(row["order_id"]),
                row["customer_id"],
                float(row["amount_usd"]),
                row["status"],
                row["failure_reason"] or None,
                row["payment_provider"],
                row["region"],
                (now - timedelta(hours=float(row["hours_ago"]))).strftime(SQLITE_DATETIME_FORMAT),
            )
            for row in csv.DictReader(handle)
        ]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DROP TABLE IF EXISTS orders")
        connection.execute(_CREATE_ORDERS)
        connection.executemany(_INSERT_ORDER, rows)
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = WarehouseSettings()
    count = seed_warehouse(settings.csv_path, settings.db_path)
    logger.info("Seeded %d orders into %s", count, settings.db_path)


if __name__ == "__main__":
    main()
