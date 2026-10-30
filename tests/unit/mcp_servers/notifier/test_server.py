import sqlite3
from contextlib import closing
from pathlib import Path

from mcp import Client

from mcp_servers.notifier.outbox_store import OutboxStore
from mcp_servers.notifier.server import create_server


async def test_send_notification_when_called_writes_outbox_row(tmp_path: Path) -> None:
    db_path = tmp_path / "notifier.db"
    server = create_server(OutboxStore(db_path))

    async with Client(server) as client:
        result = await client.call_tool(
            "send_notification",
            {
                "channel": "slack",
                "recipient": "#payments",
                "subject": "Failed orders",
                "message": "Top cause: payment_timeout",
            },
        )

    assert not result.is_error
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute("SELECT channel, recipient, subject FROM outbox").fetchall()
    assert rows == [("slack", "#payments", "Failed orders")]


async def test_list_outbox_when_two_sent_returns_newest_first(tmp_path: Path) -> None:
    server = create_server(OutboxStore(tmp_path / "notifier.db"))

    async with Client(server) as client:
        for subject in ("first", "second"):
            await client.call_tool(
                "send_notification",
                {
                    "channel": "email",
                    "recipient": "ops@example.com",
                    "subject": subject,
                    "message": "m",
                },
            )
        result = await client.call_tool("list_outbox", {})

    assert result.structured_content is not None
    subjects = [row["subject"] for row in result.structured_content["notifications"]]
    assert subjects == ["second", "first"]


async def test_send_notification_when_unknown_channel_returns_error(tmp_path: Path) -> None:
    server = create_server(OutboxStore(tmp_path / "notifier.db"))

    async with Client(server) as client:
        result = await client.call_tool(
            "send_notification",
            {"channel": "sms", "recipient": "x", "subject": "s", "message": "m"},
        )

    assert result.is_error
