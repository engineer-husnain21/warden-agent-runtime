from collections.abc import Mapping, Sequence
from typing import Any

from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from app.schemas.tool_spec import ToolSpec


class FakeToolClient:
    """Returns scripted content per qualified tool name and records every call."""

    def __init__(
        self,
        tools: Sequence[ToolSpec] = (),
        results: Mapping[str, dict[str, Any]] | None = None,
        errors: Mapping[str, str] | None = None,
    ) -> None:
        self._tools = list(tools)
        self._results = dict(results or {})
        self._errors = dict(errors or {})
        self.calls: list[ToolCall] = []
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def list_tools(self) -> list[ToolSpec]:
        return list(self._tools)

    async def call_tool(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        if call.tool in self._errors:
            return ToolResult(tool=call.tool, ok=False, error=self._errors[call.tool])
        if call.tool not in self._results:
            return ToolResult(tool=call.tool, ok=False, error=f"Unknown tool: {call.tool}")
        return ToolResult(tool=call.tool, ok=True, content=self._results[call.tool])
