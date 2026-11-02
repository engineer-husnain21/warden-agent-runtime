from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus


class RunStepResponse(BaseModel):
    """One row of a run's trace."""

    model_config = ConfigDict(from_attributes=True)

    position: int
    kind: RunStepKind
    status: RunStepStatus
    agent: str | None
    tool_name: str | None
    tool_arguments: dict[str, Any] | None
    output: dict[str, Any] | None
    policy_decision: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    created_at: datetime
