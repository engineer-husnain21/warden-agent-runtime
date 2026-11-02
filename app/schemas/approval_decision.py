from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    """A human's answer to a paused tool call; passed to the orchestrator to resume the run."""

    approved: bool
    decided_by: str = Field(min_length=1)
    reason: str | None = None
