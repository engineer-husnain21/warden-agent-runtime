from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.approval_status import ApprovalStatus


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    step_position: int
    tool_name: str
    tool_arguments: dict[str, Any]
    requested_by: str
    status: ApprovalStatus
    decided_by: str | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None
