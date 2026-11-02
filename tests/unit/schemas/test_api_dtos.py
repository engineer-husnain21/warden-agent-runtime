from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import AgentRun, RunStep
from app.schemas.agent_run_response import AgentRunResponse
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.approval_decision_request import ApprovalDecisionRequest
from app.schemas.create_agent_run_request import CreateAgentRunRequest
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_response import RunStepResponse
from app.schemas.run_step_status import RunStepStatus

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize("task", ["", "  ", "x" * 2001])
def test_create_agent_run_request_when_task_empty_fails_validation(task: str) -> None:
    with pytest.raises(ValidationError):
        CreateAgentRunRequest(task=task.strip())


def test_agent_run_response_when_built_from_entity_copies_fields() -> None:
    run = AgentRun(
        id="r1",
        task="Find failed orders",
        requested_by="oscar",
        role="operator",
        status=AgentRunStatus.AWAITING_APPROVAL,
        created_at=NOW,
        updated_at=NOW,
    )

    response = AgentRunResponse.model_validate(run)

    assert response.id == "r1"
    assert response.status is AgentRunStatus.AWAITING_APPROVAL
    assert response.completed_at is None


def test_run_step_response_when_built_from_entity_keeps_usage() -> None:
    step = RunStep(
        position=0,
        kind=RunStepKind.PLAN,
        status=RunStepStatus.SUCCEEDED,
        input_tokens=600,
        output_tokens=380,
        latency_ms=1640.0,
        cost_usd=0.00032,
        created_at=NOW,
    )

    response = RunStepResponse.model_validate(step)

    assert (response.input_tokens, response.output_tokens) == (600, 380)
    assert response.cost_usd == pytest.approx(0.00032)


def test_approval_decision_request_when_reason_too_long_fails_validation() -> None:
    with pytest.raises(ValidationError):
        ApprovalDecisionRequest(approved=False, reason="x" * 501)
