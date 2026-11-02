from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.base_agent import BaseAgent
from app.schemas.agents.planner_input import PlannerInput
from app.schemas.agents.planner_output import PlannerOutput
from app.schemas.agents.reporter_input import ReporterInput
from app.schemas.agents.reporter_output import ReporterOutput
from app.schemas.agents.step_record import StepRecord
from app.schemas.role import Role
from app.schemas.run_state import RunState
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent
from app.schemas.tool_spec import ToolSpec

GraphInput = RunState | Command[Any] | None


class AgentRunOrchestrator:
    """Runs one task as a LangGraph graph: plan, then the steps, then the final report.

    Every node publishes one StepEvent on the graph's custom stream; `stream()` yields them as
    they happen. State is checkpointed after every node, keyed by the run id.
    """

    def __init__(
        self,
        *,
        planner: BaseAgent[PlannerInput, PlannerOutput],
        reporter: BaseAgent[ReporterInput, ReporterOutput],
        checkpointer: BaseCheckpointSaver[str],
    ) -> None:
        self._planner = planner
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
        graph.add_node("plan", self._plan)
        graph.add_node("report", self._report)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "report")
        graph.add_edge("report", END)
        return graph

    async def _plan(self, state: RunState) -> dict[str, Any]:
        tools = [ToolSpec.model_validate(tool) for tool in state["tools"]]
        output = await self._planner.run(PlannerInput(task=state["task"], tools=tools))
        steps = [step.model_dump() for step in output.steps]
        _emit(
            state,
            RunStepKind.PLAN,
            RunStepStatus.SUCCEEDED,
            agent="planner",
            output={"steps": steps},
        )
        return {"steps": steps, "current": 0}

    async def _report(self, state: RunState) -> dict[str, Any]:
        records = [StepRecord.model_validate(record) for record in state.get("records", [])]
        output = await self._reporter.run(ReporterInput(task=state["task"], steps=records))
        _emit(
            state,
            RunStepKind.REPORT,
            RunStepStatus.SUCCEEDED,
            agent="reporter",
            output={"report": output.report},
        )
        return {"report": output.report}


def _emit(state: RunState, kind: RunStepKind, status: RunStepStatus, **fields: Any) -> None:
    event = StepEvent(run_id=state["run_id"], kind=kind, status=status, **fields)
    get_stream_writer()(event.model_dump(mode="json"))
