"""Warehouse MCP server. Run: `uv run python -m mcp_servers.warehouse.server` (stdio)."""

from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.warehouse.warehouse_settings import WarehouseSettings
from mcp_servers.warehouse.warehouse_store import WarehouseStore


def create_server(store: WarehouseStore) -> MCPServer:
    server = MCPServer(
        "warehouse",
        instructions="Read-only SQL access to the orders warehouse (SQLite dialect).",
    )

    @server.tool()
    def list_tables() -> dict[str, Any]:
        """List the tables in the warehouse."""
        return {"tables": store.list_tables()}

    @server.tool()
    def describe_table(table: str) -> dict[str, Any]:
        """Show the columns of one table (name, type, nullable)."""
        return {"table": table, "columns": store.describe_table(table)}

    @server.tool()
    def run_query(sql: str) -> dict[str, Any]:
        """Run one read-only SQL SELECT (SQLite dialect) and return the rows.

        Timestamps are UTC text like '2026-10-30 12:00:00', so filter recent rows with
        `created_at >= datetime('now', '-1 day')`.
        """
        rows = store.run_query(sql)
        return {"rows": rows, "row_count": len(rows)}

    return server


def main() -> None:
    settings = WarehouseSettings()
    create_server(WarehouseStore(settings.db_path)).run("stdio")


if __name__ == "__main__":
    main()
