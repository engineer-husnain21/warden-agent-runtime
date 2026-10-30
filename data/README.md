# Demo data

- `orders.csv`: about 500 synthetic e-commerce orders, used to seed the `warehouse` MCP server's read-only database.
  `hours_ago` is relative, so `uv run python -m mcp_servers.warehouse.seed` turns it into real timestamps
  at seed time. That way "failed in the last 24 hours" always has data, whenever you run the demo.
  In the last 24 hours, the top failure causes are `payment_timeout`, `inventory_unavailable` and `card_declined`.

All values are synthetic. No real customers or payments.
