from typing import Any

from pydantic import Field

from app.schemas.agents.base_agent_output import BaseAgentOutput


class ToolSelectorOutput(BaseAgentOutput):
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
