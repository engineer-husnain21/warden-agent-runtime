from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.audit_action import AuditAction


class AuditLogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str | None
    actor: str
    role: str
    action: AuditAction
    tool_name: str | None
    tool_arguments: dict[str, Any] | None
    decision: str | None
    result: dict[str, Any] | None
    created_at: datetime
