from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.base_agent import BaseAgent
from app.agents.tool_result_text import format_tool_result
from app.core.exceptions import AgentOutputError
from app.orchestrators.run_state_helpers import (
    current_step,
    emit,
    pending_call,
    record,
    result_output,
    tools_of,
)
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
        checkpointer: BaseCheckpointSaver[str],
    ) -> None:
        self._planner = planner
        self._tool_selector = tool_selector
        self._tool_executor = tool_executor
        self._step_reviewer = step_reviewer
        self._reporter = reporter
        self._graph = self._build_graph().compile(checkpointer=checkpointer)

    async def stream(
        self, run_id: str, task: str, role: Role, tools: list[ToolSpec]
    ) -> AsyncIterator[StepEvent]:
        """Start a new run and yield its events."""
        initial: RunState = {
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
        async for event in self._drive(run_id, initial):
            yield event

    async def _drive(self, run_id: str, graph_input: GraphInput) -> AsyncIterator[StepEvent]:
        config: Any = {"configurable": {"thread_id": run_id}}
        async for mode, chunk in self._graph.astream(
            graph_input, config, stream_mode=["custom", "updates"]
        ):
            if mode == "custom":
                yield StepEvent.model_validate(chunk)

    def _build_graph(self) -> StateGraph[RunState]:
        graph = StateGraph(RunState)
        for name, node in [
            ("plan", self._plan),
            ("select", self._select),
            ("execute", self._execute),
            ("review", self._review),
            ("next_step", self._next_step),
            ("report", self._report),
        ]:
            graph.add_node(name, node)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", _route_to_step_or_report, ["select", "report"])
        graph.add_conditional_edges("select", _route_after_select, ["execute", "next_step"])
        graph.add_edge("execute", "review")
        graph.add_edge("review", "next_step")
        graph.add_conditional_edges("next_step", _route_to_step_or_report, ["select", "report"])
        graph.add_edge("report", END)
        return graph

    async def _plan(self, state: RunState) -> dict[str, Any]:
        output = await self._planner.run(PlannerInput(task=state["task"], tools=tools_of(state)))
        steps = [step.model_dump() for step in output.steps]
        emit(
            state,
            RunStepKind.PLAN,
            RunStepStatus.SUCCEEDED,
            agent="planner",
            output={"steps": steps},
        )
        return {"steps": steps, "current": 0, "attempt": 0}

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
        )
        return {"pending_call": call.model_dump()}

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
        )
        outcome: StepOutcome = "succeeded" if review.ok else "failed"
        update: dict[str, Any] = {
            "records": [record(step, outcome, call.tool, result, review.feedback)]
        }
        if review.ok:
            summary = format_tool_result(result, PREVIOUS_RESULT_CHARS)
            update["previous_results"] = [f"step {state['current'] + 1} ({call.tool}): {summary}"]
        return update

    async def _next_step(self, state: RunState) -> dict[str, Any]:
        return {
            "current": state["current"] + 1,
            "attempt": 0,
            "feedback": None,
            "pending_call": None,
            "last_result": None,
        }

    async def _report(self, state: RunState) -> dict[str, Any]:
        records = [StepRecord.model_validate(item) for item in state.get("records", [])]
        output = await self._reporter.run(ReporterInput(task=state["task"], steps=records))
        emit(
            state,
            RunStepKind.REPORT,
            RunStepStatus.SUCCEEDED,
            agent="reporter",
            output={"report": output.report},
        )
        return {"report": output.report}


def _route_to_step_or_report(state: RunState) -> str:
    return "select" if state["current"] < len(state["steps"]) else "report"


def _route_after_select(state: RunState) -> str:
    return "execute" if state.get("pending_call") else "next_step"
