"""Notifier MCP server (mock). Run: `uv run python -m mcp_servers.notifier.server` (stdio)."""

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_servers.notifier.notifier_settings import NotifierSettings
from mcp_servers.notifier.outbox_store import OutboxStore

MAX_SUBJECT_LENGTH = 200
MAX_MESSAGE_LENGTH = 5000
MAX_LIST_LIMIT = 100


def create_server(store: OutboxStore) -> MCPServer:
    server = MCPServer(
        "notifier", instructions="Send team notifications (mock: written to a local outbox)."
    )

    @server.tool()
    def send_notification(
        channel: Literal["email", "slack"], recipient: str, subject: str, message: str
    ) -> dict[str, Any]:
        """Send a notification to a person or channel. This is a real write: it needs approval."""
        if not recipient.strip() or not subject.strip() or not message.strip():
            raise ToolError("recipient, subject and message must not be empty")
        if len(subject) > MAX_SUBJECT_LENGTH or len(message) > MAX_MESSAGE_LENGTH:
            raise ToolError(
                f"subject max {MAX_SUBJECT_LENGTH} and message max {MAX_MESSAGE_LENGTH} characters"
            )
        return {"sent": True, "notification": store.add(channel, recipient, subject, message)}

    @server.tool()
    def list_outbox(limit: int = 20) -> dict[str, Any]:
        """List the most recent notifications in the outbox, newest first."""
        return {"notifications": store.list_recent(max(1, min(limit, MAX_LIST_LIMIT)))}

    return server


def main() -> None:
    create_server(OutboxStore(NotifierSettings().db_path)).run("stdio")


if __name__ == "__main__":
    main()
