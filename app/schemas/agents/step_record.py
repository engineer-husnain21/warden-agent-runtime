from typing import Literal

from pydantic import BaseModel

from app.schemas.tool_result import ToolResult

StepOutcome = Literal["succeeded", "failed", "denied", "rejected", "skipped"]


class StepRecord(BaseModel):
    """What happened in one step, as input for the final report."""

    description: str
    outcome: StepOutcome
    tool: str | None = None
    result: ToolResult | None = None
    note: str = ""
