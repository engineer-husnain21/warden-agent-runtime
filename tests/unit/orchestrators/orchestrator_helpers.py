"""Shared builders for orchestrator tests: fake LLM, in-memory checkpoints, real prompts."""

from collections.abc import AsyncIterator, Sequence

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.planner_agent import PlannerAgent
from app.agents.reporter_agent import ReporterAgent
from app.core.dependencies import PROMPTS_DIR
from app.core.file_prompt_loader import FilePromptLoader
from app.orchestrators.agent_run_orchestrator import AgentRunOrchestrator
from app.schemas.step_event import StepEvent
from app.schemas.tool_spec import ToolSpec
from tests.fakes.fake_llm_client import FakeLlmClient

TOOLS = [
    ToolSpec(
        name="warehouse.run_query",
        server="warehouse",
        description="Run one read-only SQL SELECT.",
        input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
    ),
    ToolSpec(
        name="github.create_issue",
        server="github",
        description="Open a new issue.",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}}},
    ),
]


def build_orchestrator(
    llm: FakeLlmClient, checkpointer: BaseCheckpointSaver[str] | None = None
) -> AgentRunOrchestrator:
    prompts = FilePromptLoader(PROMPTS_DIR)
    return AgentRunOrchestrator(
        planner=PlannerAgent(llm, prompts),
        reporter=ReporterAgent(llm, prompts),
        checkpointer=checkpointer or InMemorySaver(),
    )


async def collect(events: AsyncIterator[StepEvent]) -> list[StepEvent]:
    return [event async for event in events]


def kinds(events: Sequence[StepEvent]) -> list[tuple[str, str]]:
    return [(event.kind.value, event.status.value) for event in events]
