from pydantic import BaseModel, Field

from app.schemas.agents.plan_step import PlanStep
from app.schemas.tool_spec import ToolSpec


class ToolSelectorInput(BaseModel):
    task: str = Field(min_length=1)
    step: PlanStep
    tools: list[ToolSpec]
    previous_results: list[str] = Field(default_factory=list)
    feedback: str | None = None
