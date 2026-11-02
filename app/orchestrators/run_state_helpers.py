"""Small helpers for AgentRunOrchestrator: read typed values out of RunState and publish events."""

from typing import Any

from langgraph.config import get_stream_writer

from app.schemas.agents.plan_step import PlanStep
from app.schemas.agents.step_record import StepOutcome, StepRecord
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


def approval_request(state: RunState) -> dict[str, Any]:
    """Payload passed to `interrupt()` and shown to the human who approves."""
    call = pending_call(state)
    return {
        "step_index": state["current"],
        "step": current_step(state).description,
        "tool": call.tool,
        "arguments": call.arguments,
    }
