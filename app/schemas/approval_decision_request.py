from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=500)
