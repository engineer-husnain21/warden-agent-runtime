"""Warehouse MCP server. Run: `uv run python -m mcp_servers.warehouse.server` (stdio)."""

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_servers.warehouse.seed import seed_warehouse
from mcp_servers.warehouse.warehouse_settings import WarehouseSettings
from mcp_servers.warehouse.warehouse_store import WarehouseStore

RUN_QUERY_DESCRIPTION = """Run one read-only SQL SELECT (SQLite dialect) and return the rows.

Timestamps are UTC text like '2026-10-30 12:00:00', so filter recent rows with
`created_at >= datetime('now', '-1 day')`. Large results are cut off (`truncated`):
prefer GROUP BY / LIMIT.

Tables:
{schema}"""


def describe_schema(store: WarehouseStore) -> str:
    """`table(column TYPE, ...)` per line, read from the database so it is never out of date."""
    try:
        lines = []
        for table in store.list_tables():
            columns = ", ".join(f"{c['name']} {c['type']}" for c in store.describe_table(table))
            lines.append(f"- {table}({columns})")
        return "\n".join(lines)
    except ToolError:
        return "- (unknown: database not seeded yet; use list_tables / describe_table)"


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

    @server.tool(description=RUN_QUERY_DESCRIPTION.format(schema=describe_schema(store)))
    def run_query(sql: str) -> dict[str, Any]:
        rows, truncated = store.run_query(sql)
        return {"rows": rows, "row_count": len(rows), "truncated": truncated}

    return server


def build_store(settings: WarehouseSettings) -> WarehouseStore:
    """Re-seed first when WAREHOUSE_SEED_ON_STARTUP is on, then open the store read-only."""
    if settings.seed_on_startup:
        seed_warehouse(settings.csv_path, settings.db_path)
    return WarehouseStore(settings.db_path, settings.max_rows)


def main() -> None:
    create_server(build_store(WarehouseSettings())).run("stdio")


if __name__ == "__main__":
    main()
