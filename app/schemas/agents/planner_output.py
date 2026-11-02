from pydantic import Field

from app.schemas.agents.base_agent_output import BaseAgentOutput
from app.schemas.agents.plan_step import PlanStep

MAX_PLAN_STEPS = 8


class PlannerOutput(BaseAgentOutput):
    """Ordered steps. Empty when the task cannot be done with the available tools."""

    steps: list[PlanStep] = Field(max_length=MAX_PLAN_STEPS)
