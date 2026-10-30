import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError


class WarehouseStore:
    """Read-only access to the warehouse SQLite file. Every call opens the file in `mode=ro`."""

    def __init__(self, db_path: Path) -> None:
        self._uri = f"{db_path.resolve().as_uri()}?mode=ro"

    def list_tables(self) -> list[str]:
        rows = self._fetch(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    def describe_table(self, table: str) -> list[dict[str, Any]]:
        if table not in self.list_tables():
            raise ToolError(f"Unknown table: {table}")
        # The name is checked against the real table list above, so quoting it here is safe.
        rows = self._fetch(f'PRAGMA table_info("{table}")')
        return [
            {"name": row["name"], "type": row["type"], "nullable": not row["notnull"]}
            for row in rows
        ]

    def run_query(self, sql: str) -> list[dict[str, Any]]:
        return self._fetch(sql)

    def _fetch(self, sql: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self._uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            try:
                rows = connection.execute(sql).fetchall()
            except sqlite3.Error as error:
                raise ToolError(f"Query failed: {error}") from error
        return [dict(row) for row in rows]
