import asyncio
import time
from collections.abc import Mapping
from contextlib import AsyncExitStack

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from app.schemas.tool_spec import ToolSpec

logger = get_logger(__name__)


class McpToolClient:
    """ToolClient over MCP: one stdio subprocess per server, tools named `<server>.<tool>`.

    The MCP sessions are opened and closed inside one background task that this client
    owns, because anyio requires both to happen in the same task. `connect()`/`close()`
    can therefore be called from any task (app lifespan, test fixtures, ...).
    """

    def __init__(
        self, servers: Mapping[str, StdioServerParameters], timeout_seconds: float = 60.0
    ) -> None:
        self._servers = dict(servers)
        self._timeout_seconds = timeout_seconds
        self._clients: dict[str, Client] = {}
        self._runner: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._starting: str | None = None

    async def connect(self) -> None:
        if self._runner is not None:
            return
        self._ready.clear()
        self._stop.clear()
        runner = asyncio.create_task(self._hold_sessions(), name="mcp-sessions")
        await self._ready.wait()
        if runner.done() and runner.exception() is not None:
            failed = self._starting or "unknown"
            raise ExternalServiceError(
                f"Could not start MCP server '{failed}'", details={"server": failed}
            ) from runner.exception()
        self._runner = runner
        logger.info("Connected to MCP servers: %s", ", ".join(self._clients))

    async def close(self) -> None:
        if self._runner is None:
            return
        self._stop.set()
        try:
            await self._runner
        except Exception:
            logger.exception("Error while closing MCP sessions")
        self._runner = None

    async def list_tools(self) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for server, client in self._clients.items():
            listing = await client.list_tools()
            specs.extend(
                ToolSpec(
                    name=f"{server}.{tool.name}",
                    server=server,
                    description=tool.description or "",
                    input_schema=tool.input_schema,
                )
                for tool in listing.tools
            )
        return specs

    async def call_tool(self, call: ToolCall) -> ToolResult:
        client = self._clients.get(call.server)
        if client is None:
            return ToolResult(tool=call.tool, ok=False, error=f"Unknown tool server: {call.server}")

        started = time.perf_counter()
        try:
            result = await client.call_tool(call.tool_name, call.arguments)
        except Exception as error:
            logger.warning("MCP call %s failed: %s", call.tool, error)
            return ToolResult(tool=call.tool, ok=False, error=str(error) or type(error).__name__)
        latency_ms = (time.perf_counter() - started) * 1000
        return _to_tool_result(call.tool, result, latency_ms)

    async def _hold_sessions(self) -> None:
        try:
            async with AsyncExitStack() as stack:
                for name, params in self._servers.items():
                    self._starting = name
                    client = Client(params, read_timeout_seconds=self._timeout_seconds)
                    self._clients[name] = await stack.enter_async_context(client)
                self._starting = None
                self._ready.set()
                await self._stop.wait()
        finally:
            self._clients.clear()
            self._ready.set()


def _to_tool_result(tool: str, result: CallToolResult, latency_ms: float) -> ToolResult:
    text = "\n".join(block.text for block in result.content if isinstance(block, TextContent))
    if result.is_error:
        return ToolResult(tool=tool, ok=False, error=text or "Tool failed", latency_ms=latency_ms)
    content = result.structured_content if result.structured_content is not None else {"text": text}
    return ToolResult(tool=tool, ok=True, content=content, latency_ms=latency_ms)
