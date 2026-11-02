from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.agent_run_status import AgentRunStatus


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task: str
    requested_by: str
    role: str
    status: AgentRunStatus
    error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
