"""Shared builders for orchestrator tests: fake LLM, fake tools, in-memory checkpoints."""

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.planner_agent import PlannerAgent
from app.agents.reporter_agent import ReporterAgent
from app.agents.step_reviewer_agent import StepReviewerAgent
from app.agents.tool_catalog_agent import ToolCatalogAgent
from app.agents.tool_executor_agent import ToolExecutorAgent
from app.agents.tool_selector_agent import ToolSelectorAgent
from app.core.config import Settings
from app.core.dependencies import PROMPTS_DIR
from app.core.file_prompt_loader import FilePromptLoader
from app.orchestrators.agent_run_orchestrator import AgentRunOrchestrator
from app.policies.step_retry_policy import StepRetryPolicy
from app.policies.tool_permission_policy import ToolPermissionPolicy
from app.schemas.step_event import StepEvent
from app.schemas.tool_spec import ToolSpec
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient

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
    llm: FakeLlmClient,
    tools: FakeToolClient | None = None,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    max_steps: int = 8,
    max_step_retries: int = 1,
    catalog: Sequence[ToolSpec] = TOOLS,
) -> AgentRunOrchestrator:
    """`catalog` is what the run can plan with; `tools` is the fake that executes calls."""
    prompts = FilePromptLoader(PROMPTS_DIR)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    return AgentRunOrchestrator(
        tool_catalog=ToolCatalogAgent(llm, prompts, FakeToolClient(tools=catalog)),
        planner=PlannerAgent(llm, prompts),
        tool_selector=ToolSelectorAgent(llm, prompts),
        tool_executor=ToolExecutorAgent(llm, prompts, tools or FakeToolClient()),
        step_reviewer=StepReviewerAgent(llm, prompts),
        reporter=ReporterAgent(llm, prompts),
        policy=ToolPermissionPolicy(settings.tool_permission_rules),
        retry_policy=StepRetryPolicy(settings.read_only_tools),
        checkpointer=checkpointer or InMemorySaver(),
        max_steps=max_steps,
        max_step_retries=max_step_retries,
    )


def plan(*descriptions: str) -> str:
    return json.dumps({"steps": [{"description": d} for d in descriptions]})


def select(tool: str, **arguments: Any) -> str:
    return json.dumps({"tool": tool, "arguments": arguments, "reasoning": "fits the step"})


def review(ok: bool, feedback: str = "") -> str:
    return json.dumps({"ok": ok, "feedback": feedback})


async def collect(events: AsyncIterator[StepEvent]) -> list[StepEvent]:
    return [event async for event in events]


def kinds(events: Sequence[StepEvent]) -> list[tuple[str, str]]:
    return [(event.kind.value, event.status.value) for event in events]
