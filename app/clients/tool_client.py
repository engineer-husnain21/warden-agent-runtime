from typing import Protocol

from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from app.schemas.tool_spec import ToolSpec


class ToolClient(Protocol):
    """Access to every tool the runtime may call. The only way the app reaches MCP servers."""

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def list_tools(self) -> list[ToolSpec]: ...

    async def call_tool(self, call: ToolCall) -> ToolResult: ...
