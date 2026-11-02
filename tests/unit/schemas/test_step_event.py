from app.schemas.approval_decision import ApprovalDecision
from app.schemas.policy_decision import PolicyDecision
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent


def test_step_event_when_serialised_roundtrips() -> None:
    event = StepEvent(
        run_id="r1",
        kind=RunStepKind.PERMISSION_CHECK,
        status=RunStepStatus.DENIED,
        step_index=1,
        tool_name="github.create_issue",
        tool_arguments={"title": "t"},
        policy_decision=PolicyDecision.DENY,
    )

    restored = StepEvent.model_validate_json(event.model_dump_json())

    assert restored == event
    assert restored.model_dump(mode="json")["policy_decision"] == "deny"


def test_approval_decision_when_rejected_keeps_reason() -> None:
    decision = ApprovalDecision(approved=False, decided_by="ada", reason="duplicate")

    assert decision.model_dump() == {"approved": False, "decided_by": "ada", "reason": "duplicate"}
