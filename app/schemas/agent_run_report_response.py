from pydantic import BaseModel

from app.schemas.agent_run_status import AgentRunStatus


class AgentRunReportResponse(BaseModel):
    """The final Markdown report; `report` is null until the run completes."""

    run_id: str
    status: AgentRunStatus
    report: str | None
