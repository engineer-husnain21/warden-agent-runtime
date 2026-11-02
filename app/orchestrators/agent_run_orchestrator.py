from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.base_agent import BaseAgent
from app.agents.tool_result_text import format_tool_result
from app.core.exceptions import AgentOutputError
from app.orchestrators.run_graph_routes import (
    awaiting_approval_event,
    route_after_approval,
    route_after_permission,
    route_after_review,
    route_after_select,
    route_to_step_or_report,
)
from app.orchestrators.run_state_helpers import (
    PERMISSION_STATUS,
    approval_request,
    current_step,
    emit,
    initial_state,
    next_step_update,
    pending_call,
    record,
    result_output,
    tools_of,
)
from app.policies.tool_permission_policy import ToolPermissionPolicy
from app.schemas.agents.planner_input import PlannerInput
from app.schemas.agents.planner_output import PlannerOutput
from app.schemas.agents.reporter_input import ReporterInput
from app.schemas.agents.reporter_output import ReporterOutput
from app.schemas.agents.step_record import StepOutcome, StepRecord
from app.schemas.agents.step_reviewer_input import StepReviewerInput
from app.schemas.agents.step_reviewer_output import StepReviewerOutput
from app.schemas.agents.tool_executor_input import ToolExecutorInput
from app.schemas.agents.tool_executor_output import ToolExecutorOutput
from app.schemas.agents.tool_selector_input import ToolSelectorInput
from app.schemas.agents.tool_selector_output import ToolSelectorOutput
from app.schemas.approval_decision import ApprovalDecision
from app.schemas.policy_decision import PolicyDecision
from app.schemas.role import Role
from app.schemas.run_state import RunState
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from app.schemas.tool_spec import ToolSpec

GraphInput = RunState | Command[Any] | None
PREVIOUS_RESULT_CHARS = 1500
# Key LangGraph uses in "updates" stream chunks when a node called interrupt().
INTERRUPT_KEY = "__interrupt__"


class AgentRunOrchestrator:
    """Runs one task as a LangGraph graph: plan, then per step select → execute → review,
    then the final report.

    Every node publishes one StepEvent on the graph's custom stream; `stream()` yields them as
    they happen. State is checkpointed after every node, keyed by the run id.
    """

    def __init__(
        self,
        *,
        planner: BaseAgent[PlannerInput, PlannerOutput],
        tool_selector: BaseAgent[ToolSelectorInput, ToolSelectorOutput],
        tool_executor: BaseAgent[ToolExecutorInput, ToolExecutorOutput],
        step_reviewer: BaseAgent[StepReviewerInput, StepReviewerOutput],
        reporter: BaseAgent[ReporterInput, ReporterOutput],
        policy: ToolPermissionPolicy,
        checkpointer: BaseCheckpointSaver[str],
        max_steps: int,
        max_step_retries: int,
    ) -> None:
        self._planner = planner
        self._tool_selector = tool_selector
        self._tool_executor = tool_executor
        self._step_reviewer = step_reviewer
        self._reporter = reporter
        self._policy = policy
        self._max_steps = max_steps
        self._max_step_retries = max_step_retries
        self._graph = self._build_graph().compile(checkpointer=checkpointer)

    async def stream(
        self, run_id: str, task: str, role: Role, tools: list[ToolSpec]
    ) -> AsyncIterator[StepEvent]:
        """Start a new run and yield its events."""
        initial = initial_state(run_id, task, role, tools)
        async for event in self._drive(run_id, initial):
            yield event

    async def resume(
        self, run_id: str, decision: ApprovalDecision | None = None
    ) -> AsyncIterator[StepEvent]:
        """Continue a run from its last checkpoint.

        With a decision: answer the pending approval. Without one: pick up a run that was
        interrupted by a crash or restart; finished nodes are not run again.
        """
        graph_input: GraphInput = (
            Command(resume=decision.model_dump()) if decision is not None else None
        )
        async for event in self._drive(run_id, graph_input):
            yield event

    async def _drive(self, run_id: str, graph_input: GraphInput) -> AsyncIterator[StepEvent]:
        config: Any = {"configurable": {"thread_id": run_id}}
        async for mode, chunk in self._graph.astream(
            graph_input, config, stream_mode=["custom", "updates"]
        ):
            if mode == "custom":
                yield StepEvent.model_validate(chunk)
            elif isinstance(chunk, dict) and INTERRUPT_KEY in chunk:
                # The graph paused in `await_approval`. Report it from the interrupt payload:
                # the node itself emits nothing before `interrupt()`, because LangGraph re-runs
                # it from the start on resume.
                for paused in chunk[INTERRUPT_KEY]:
                    yield awaiting_approval_event(run_id, paused.value)

    def _build_graph(self) -> StateGraph[RunState]:
        graph = StateGraph(RunState)
        for name, node in [
            ("plan", self._plan),
            ("select", self._select),
            ("check_permission", self._check_permission),
            ("await_approval", self._await_approval),
            ("execute", self._execute),
            ("review", self._review),
            ("next_step", self._next_step),
            ("report", self._report),
        ]:
            graph.add_node(name, node)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", route_to_step_or_report, ["select", "report"])
        graph.add_conditional_edges("select", route_after_select, ["check_permission", "next_step"])
        graph.add_conditional_edges(
            "check_permission",
            route_after_permission,
            ["execute", "await_approval", "next_step"],
        )
        graph.add_conditional_edges(
            "await_approval", route_after_approval, ["execute", "next_step"]
        )
        graph.add_edge("execute", "review")
        graph.add_conditional_edges("review", route_after_review, ["select", "next_step"])
        graph.add_conditional_edges("next_step", route_to_step_or_report, ["select", "report"])
        graph.add_edge("report", END)
        return graph

    async def _plan(self, state: RunState) -> dict[str, Any]:
        output = await self._planner.run(PlannerInput(task=state["task"], tools=tools_of(state)))
        steps = [step.model_dump() for step in output.steps[: self._max_steps]]
        dropped = len(output.steps) - len(steps)
        emit(
            state,
            RunStepKind.PLAN,
            RunStepStatus.SUCCEEDED,
            agent="planner",
            output={"steps": steps, "dropped_steps": dropped},
            usage=output.usage,
        )
        return {"steps": steps, "current": 0, "attempt": 0, "retrying": False}

    async def _select(self, state: RunState) -> dict[str, Any]:
        step = current_step(state)
        try:
            selection = await self._tool_selector.run(
                ToolSelectorInput(
                    task=state["task"],
                    step=step,
                    tools=tools_of(state),
                    previous_results=state.get("previous_results", []),
                    feedback=state.get("feedback"),
                )
            )
        except AgentOutputError as error:
            emit(
                state,
                RunStepKind.TOOL_SELECTION,
                RunStepStatus.FAILED,
                agent="tool_selector",
                output={"error": error.message},
            )
            return {"pending_call": None, "records": [record(step, "failed", note=error.message)]}
        call = ToolCall(tool=selection.tool, arguments=selection.arguments)
        emit(
            state,
            RunStepKind.TOOL_SELECTION,
            RunStepStatus.SUCCEEDED,
            agent="tool_selector",
            tool_name=call.tool,
            tool_arguments=call.arguments,
            output={"reasoning": selection.reasoning},
            usage=selection.usage,
        )
        return {"pending_call": call.model_dump()}

    async def _check_permission(self, state: RunState) -> dict[str, Any]:
        call, role = pending_call(state), Role(state["role"])
        decision = self._policy.decide(call.tool, role)
        status = PERMISSION_STATUS[decision]
        emit(
            state,
            RunStepKind.PERMISSION_CHECK,
            status,
            tool_name=call.tool,
            tool_arguments=call.arguments,
            policy_decision=decision,
        )
        update: dict[str, Any] = {"policy_decision": decision.value}
        if decision is PolicyDecision.DENY:
            note = f"Denied: role '{role.value}' may not call {call.tool}"
            update["records"] = [record(current_step(state), "denied", call.tool, note=note)]
        return update

    async def _await_approval(self, state: RunState) -> dict[str, Any]:
        step, call = current_step(state), pending_call(state)
        answer = interrupt(approval_request(state))
        decision = ApprovalDecision.model_validate(answer)
        emit(
            state,
            RunStepKind.APPROVAL,
            RunStepStatus.SUCCEEDED if decision.approved else RunStepStatus.DENIED,
            tool_name=call.tool,
            tool_arguments=call.arguments,
            output=decision.model_dump(),
        )
        update: dict[str, Any] = {"approval": decision.model_dump()}
        if not decision.approved:
            note = f"Rejected by {decision.decided_by}: {decision.reason or 'no reason given'}"
            update["records"] = [record(step, "rejected", call.tool, note=note)]
        return update

    async def _execute(self, state: RunState) -> dict[str, Any]:
        call = pending_call(state)
        output = await self._tool_executor.run(ToolExecutorInput(call=call))
        result = output.result
        status = RunStepStatus.SUCCEEDED if result.ok else RunStepStatus.FAILED
        emit(
            state,
            RunStepKind.TOOL_CALL,
            status,
            agent="tool_executor",
            tool_name=call.tool,
            tool_arguments=call.arguments,
            output=result_output(result),
        )
        return {"last_result": result.model_dump()}

    async def _review(self, state: RunState) -> dict[str, Any]:
        step, call = current_step(state), pending_call(state)
        result = ToolResult.model_validate(state["last_result"])
        review = await self._step_reviewer.run(
            StepReviewerInput(task=state["task"], step=step, call=call, result=result)
        )
        status = RunStepStatus.SUCCEEDED if review.ok else RunStepStatus.FAILED
        emit(
            state,
            RunStepKind.REVIEW,
            status,
            agent="step_reviewer",
            tool_name=call.tool,
            output={"ok": review.ok, "feedback": review.feedback},
            usage=review.usage,
        )
        attempt = state.get("attempt", 0)
        if not review.ok and attempt < self._max_step_retries:
            # Try the step again; the selector gets the reviewer's feedback.
            return {"attempt": attempt + 1, "retrying": True, "feedback": review.feedback}
        outcome: StepOutcome = "succeeded" if review.ok else "failed"
        update: dict[str, Any] = {
            "retrying": False,
            "records": [record(step, outcome, call.tool, result, review.feedback)],
        }
        if review.ok:
            summary = format_tool_result(result, PREVIOUS_RESULT_CHARS)
            update["previous_results"] = [f"step {state['current'] + 1} ({call.tool}): {summary}"]
        return update

    async def _next_step(self, state: RunState) -> dict[str, Any]:
        return next_step_update(state)

    async def _report(self, state: RunState) -> dict[str, Any]:
        records = [StepRecord.model_validate(item) for item in state.get("records", [])]
        output = await self._reporter.run(ReporterInput(task=state["task"], steps=records))
        emit(
            state,
            RunStepKind.REPORT,
            RunStepStatus.SUCCEEDED,
            agent="reporter",
            output={"report": output.report},
            usage=output.usage,
        )
        return {"report": output.report}
