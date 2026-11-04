"""Small helpers for AgentRunOrchestrator: read typed values out of RunState and publish events."""

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.tool_result_text import format_tool_result
from app.schemas.agents.plan_step import PlanStep
from app.schemas.agents.step_record import StepOutcome, StepRecord
from app.schemas.agents.step_reviewer_output import StepReviewerOutput
from app.schemas.policy_decision import PolicyDecision
from app.schemas.role import Role
from app.schemas.run_state import RunState
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from app.schemas.tool_spec import ToolSpec

_RUN_LEVEL_KINDS = {RunStepKind.PLAN, RunStepKind.REPORT}
# How much of a successful step's result the next steps' tool selector gets to see.
PREVIOUS_RESULT_CHARS = 1500


def emit(state: RunState, kind: RunStepKind, status: RunStepStatus, **fields: Any) -> None:
    """Publish one StepEvent on the graph's custom stream (plan/report have no step index)."""
    step_index = None if kind in _RUN_LEVEL_KINDS else state.get("current")
    event = StepEvent(
        run_id=state["run_id"], kind=kind, status=status, step_index=step_index, **fields
    )
    get_stream_writer()(event.model_dump(mode="json"))


def tools_of(state: RunState) -> list[ToolSpec]:
    return [ToolSpec.model_validate(tool) for tool in state["tools"]]


def current_step(state: RunState) -> PlanStep:
    return PlanStep.model_validate(state["steps"][state["current"]])


def pending_call(state: RunState) -> ToolCall:
    return ToolCall.model_validate(state["pending_call"])


def result_output(result: ToolResult) -> dict[str, Any]:
    return (result.content or {}) if result.ok else {"error": result.error}


def record(
    step: PlanStep,
    outcome: StepOutcome,
    tool: str | None = None,
    result: ToolResult | None = None,
    note: str = "",
) -> dict[str, Any]:
    step_record = StepRecord(
        description=step.description, outcome=outcome, tool=tool, result=result, note=note
    )
    return step_record.model_dump()


PERMISSION_STATUS = {
    PolicyDecision.ALLOW: RunStepStatus.SUCCEEDED,
    PolicyDecision.DENY: RunStepStatus.DENIED,
    PolicyDecision.NEEDS_APPROVAL: RunStepStatus.AWAITING_APPROVAL,
}


def initial_state(run_id: str, task: str, role: Role, tools: list[ToolSpec]) -> RunState:
    return {
        "run_id": run_id,
        "task": task,
        "role": role.value,
        "tools": [tool.model_dump() for tool in tools],
        "steps": [],
        "current": 0,
        "attempt": 0,
        "records": [],
        "previous_results": [],
    }


def next_step_update(state: RunState) -> dict[str, Any]:
    """Move to the next plan step and clear everything that belonged to the current one."""
    return {
        "current": state["current"] + 1,
        "attempt": 0,
        "retrying": False,
        "feedback": None,
        "pending_call": None,
        "policy_decision": None,
        "approval": None,
        "last_result": None,
    }


WRITE_KEPT_WARNING = "The write already ran, so it is not repeated."


def review_update(
    state: RunState,
    review: StepReviewerOutput,
    result: ToolResult,
    max_retries: int,
    may_retry: bool,
) -> dict[str, Any]:
    """After a review: retry the step with the reviewer's feedback, or record its outcome.

    `may_retry` is False when a write already ran (StepRetryPolicy). Then a rejected review
    does not fail the step: the write is kept and the reviewer's note becomes a warning.
    """
    attempt = state.get("attempt", 0)
    if not review.ok and may_retry and attempt < max_retries:
        return {"attempt": attempt + 1, "retrying": True, "feedback": review.feedback}
    step, call = current_step(state), pending_call(state)
    kept_write = not review.ok and not may_retry
    outcome: StepOutcome = "succeeded" if review.ok or kept_write else "failed"
    note = (
        f"Reviewer warning: {review.feedback} {WRITE_KEPT_WARNING}"
        if kept_write
        else review.feedback
    )
    update: dict[str, Any] = {
        "retrying": False,
        "records": [record(step, outcome, call.tool, result, note)],
    }
    if outcome == "succeeded":
        summary = format_tool_result(result, PREVIOUS_RESULT_CHARS)
        update["previous_results"] = [f"step {state['current'] + 1} ({call.tool}): {summary}"]
    return update


def approval_request(state: RunState) -> dict[str, Any]:
    """Payload passed to `interrupt()` and shown to the human who approves."""
    call = pending_call(state)
    return {
        "step_index": state["current"],
        "step": current_step(state).description,
        "tool": call.tool,
        "arguments": call.arguments,
    }
