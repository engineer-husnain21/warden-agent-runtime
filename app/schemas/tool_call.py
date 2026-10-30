from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A request to run one tool, e.g. `ToolCall(tool="warehouse.run_query", arguments={...})`."""

    tool: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    arguments: dict[str, Any] = Field(default_factory=dict)

    @property
    def server(self) -> str:
        return self.tool.split(".", 1)[0]

    @property
    def tool_name(self) -> str:
        return self.tool.split(".", 1)[1]
