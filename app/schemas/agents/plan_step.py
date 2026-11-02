from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """One step of a plan; each step is done with exactly one tool call."""

    description: str = Field(min_length=1, max_length=500)
