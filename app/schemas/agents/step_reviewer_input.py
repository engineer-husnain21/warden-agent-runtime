from pydantic import BaseModel, Field

from app.schemas.agents.plan_step import PlanStep
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult


class StepReviewerInput(BaseModel):
    task: str = Field(min_length=1)
    step: PlanStep
    call: ToolCall
    result: ToolResult
