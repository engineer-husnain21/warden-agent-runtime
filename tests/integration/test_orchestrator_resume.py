"""Durable runs: a crash mid-run resumes from the last SQLite checkpoint, not from the start."""

from pathlib import Path

import pytest

from app.repositories.checkpoint_repository import CheckpointRepository
from app.schemas.role import Role
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient
from tests.unit.orchestrators.orchestrator_helpers import (
    build_orchestrator,
    collect,
    kinds,
    plan,
    review,
    select,
)

TASK = "Count failed orders, then open an issue about them"


class _CrashingToolClient(FakeToolClient):
    """Simulates the process dying while a tool runs."""

    async def call_tool(self, call: ToolCall) -> ToolResult:
        if call.tool == "github.create_issue":
            self.calls.append(call)
            raise RuntimeError("process killed")
        return await super().call_tool(call)


async def test_resume_when_crash_after_step_one_does_not_rerun_step_one(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{(tmp_path / 'checkpoints.db').as_posix()}"

    # First process: step 1 completes, step 2 crashes inside the tool call.
    first_llm = FakeLlmClient(
        [
            plan("Count failed orders", "Open an issue about them"),
            select("warehouse.run_query", sql="SELECT COUNT(*) AS n FROM orders"),
            review(True),
            select("github.create_issue", title="35 failed orders"),
        ]
    )
    first_tools = _CrashingToolClient(results={"warehouse.run_query": {"rows": [{"n": 35}]}})
    first_repo = CheckpointRepository(url)
    crashed = build_orchestrator(first_llm, first_tools, checkpointer=await first_repo.open())
    with pytest.raises(RuntimeError, match="process killed"):
        await collect(crashed.stream("run-crash", TASK, Role.ADMIN))
    await first_repo.close()

    # Second process: new orchestrator, same checkpoint file, resume without input.
    second_llm = FakeLlmClient([review(True), "## Summary\n35 failed orders; issue #7 opened."])
    second_tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 7}}})
    second_repo = CheckpointRepository(url)
    restarted = build_orchestrator(second_llm, second_tools, checkpointer=await second_repo.open())
    events = await collect(restarted.resume("run-crash"))
    await second_repo.close()

    assert kinds(events) == [
        ("tool_call", "succeeded"),
        ("review", "succeeded"),
        ("report", "succeeded"),
    ]
    # Only the interrupted tool call ran again; plan, step 1 and step 2's selection did not.
    assert [call.tool for call in second_tools.calls] == ["github.create_issue"]
    assert len(second_llm.calls) == 2
    report_prompt = second_llm.calls[-1][1].content
    assert "1. Count failed orders [succeeded]" in report_prompt
    assert "2. Open an issue about them [succeeded]" in report_prompt
