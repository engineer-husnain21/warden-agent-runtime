"""Edge routing for the AgentRunOrchestrator graph. Each function reads RunState and names the
next node. Kept apart so the graph's control flow can be read in one place."""

from typing import Any

from app.schemas.policy_decision import PolicyDecision
from app.schemas.run_state import RunState
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent


def route_to_step_or_report(state: RunState) -> str:
    return "select" if state["current"] < len(state["steps"]) else "report"


def route_after_select(state: RunState) -> str:
    return "check_permission" if state.get("pending_call") else "next_step"


def route_after_permission(state: RunState) -> str:
    decision = state.get("policy_decision")
    if decision == PolicyDecision.ALLOW:
        return "execute"
    if decision == PolicyDecision.NEEDS_APPROVAL:
        return "await_approval"
    return "next_step"


def route_after_approval(state: RunState) -> str:
    approval = state.get("approval") or {}
    return "execute" if approval.get("approved") else "next_step"


def route_after_review(state: RunState) -> str:
    return "select" if state.get("retrying") else "next_step"


def awaiting_approval_event(run_id: str, payload: dict[str, Any]) -> StepEvent:
    """The event for a run paused in `await_approval`, built from the interrupt payload."""
    return StepEvent(
        run_id=run_id,
        kind=RunStepKind.APPROVAL,
        status=RunStepStatus.AWAITING_APPROVAL,
        step_index=payload["step_index"],
        tool_name=payload["tool"],
        tool_arguments=payload["arguments"],
        output={"step": payload["step"]},
        policy_decision=PolicyDecision.NEEDS_APPROVAL,
    )
