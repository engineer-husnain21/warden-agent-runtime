import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

_READ_ONLY_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
# Everything a plain SELECT needs; any other action (writes, PRAGMA, ATTACH, ...) is denied.
_ALLOWED_ACTIONS = frozenset(
    {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
)


class WarehouseStore:
    """Read-only access to the warehouse SQLite file.

    Three layers keep `run_query` read-only: only one SELECT/WITH statement is accepted,
    a SQLite authorizer denies every non-read action, and the file is opened in `mode=ro`.
    """

    def __init__(self, db_path: Path, max_rows: int = 200) -> None:
        self._uri = f"{db_path.resolve().as_uri()}?mode=ro"
        self._max_rows = max_rows

    def list_tables(self) -> list[str]:
        rows, _ = self._fetch(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    def describe_table(self, table: str) -> list[dict[str, Any]]:
        if table not in self.list_tables():
            raise ToolError(f"Unknown table: {table}")
        # The name is checked against the real table list above, so quoting it here is safe.
        rows, _ = self._fetch(f'PRAGMA table_info("{table}")')
        return [
            {"name": row["name"], "type": row["type"], "nullable": not row["notnull"]}
            for row in rows
        ]

    def run_query(self, sql: str) -> tuple[list[dict[str, Any]], bool]:
        """Run one SELECT. Returns at most `max_rows` rows and whether more were cut off."""
        statement = sql.strip().rstrip(";").strip()
        if ";" in statement:
            raise ToolError("Only one SQL statement is allowed")
        if not _READ_ONLY_START.match(statement):
            raise ToolError("Only SELECT (or WITH ... SELECT) queries are allowed")
        return self._fetch(statement, read_only=True)

    def _fetch(self, sql: str, read_only: bool = False) -> tuple[list[dict[str, Any]], bool]:
        with closing(sqlite3.connect(self._uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            if read_only:
                connection.set_authorizer(_allow_reads_only)
            try:
                rows = connection.execute(sql).fetchmany(self._max_rows + 1)
            except sqlite3.Error as error:
                raise ToolError(f"Query failed: {error}") from error
        truncated = len(rows) > self._max_rows
        return [dict(row) for row in rows[: self._max_rows]], truncated


def _allow_reads_only(action: int, *_args: str | None) -> int:
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY
