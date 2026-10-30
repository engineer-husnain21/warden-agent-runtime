from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """What came back from one tool call. Tool-side failures are `ok=False`, not exceptions."""

    tool: str
    ok: bool
    content: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float = Field(default=0.0, ge=0)
