import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CREATE_OUTBOX = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


class OutboxStore:
    """SQLite outbox: every 'sent' notification is one row. Nothing leaves this machine."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path)) as connection, connection:
            connection.execute(_CREATE_OUTBOX)

    def add(self, channel: str, recipient: str, subject: str, message: str) -> dict[str, Any]:
        created_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        with closing(sqlite3.connect(self._db_path)) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO outbox (channel, recipient, subject, message, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (channel, recipient, subject, message, created_at),
            )
        return {
            "id": cursor.lastrowid,
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "created_at": created_at,
        }

    def list_recent(self, limit: int) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self._db_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM outbox ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
