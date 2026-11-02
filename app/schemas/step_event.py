from typing import Any

from pydantic import BaseModel

from app.schemas.policy_decision import PolicyDecision
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus


class StepEvent(BaseModel):
    """One thing that happened in a run, yielded by the orchestrator as it happens.

    The service turns each event into a RunStep row and, where relevant, an audit entry.
    """

    run_id: str
    kind: RunStepKind
    status: RunStepStatus
    agent: str | None = None
    step_index: int | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    policy_decision: PolicyDecision | None = None
