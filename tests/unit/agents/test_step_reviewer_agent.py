from typing import Any

from app.agents.step_reviewer_agent import StepReviewerAgent
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.plan_step import PlanStep
from app.schemas.agents.step_reviewer_input import StepReviewerInput
from app.schemas.tool_call import ToolCall
from app.schemas.tool_result import ToolResult
from tests.fakes.fake_llm_client import FakeLlmClient

CALL = ToolCall(tool="warehouse.run_query", arguments={"sql": "SELECT * FROM orders WHERE 0"})


def _input(ok: bool = True, content: dict[str, Any] | None = None) -> StepReviewerInput:
    result = ToolResult(
        tool=CALL.tool, ok=ok, content=content, error=None if ok else "Query failed: no table"
    )
    return StepReviewerInput(
        task="Find failed orders",
        step=PlanStep(description="Count failed orders in the last 24 hours"),
        call=CALL,
        result=result,
    )


async def test_run_when_result_empty_returns_not_ok(prompt_loader: FilePromptLoader) -> None:
    llm = FakeLlmClient(['{"ok": false, "feedback": "No rows; filter on status = \'failed\'."}'])

    output = await StepReviewerAgent(llm, prompt_loader).run(_input(content={"rows": []}))

    assert not output.ok
    assert "status" in output.feedback
    assert len(output.usage) == 1
    assert '{"rows": []}' in llm.calls[0][1].content


async def test_run_when_result_good_returns_ok(prompt_loader: FilePromptLoader) -> None:
    llm = FakeLlmClient(['{"ok": true, "feedback": ""}'])

    output = await StepReviewerAgent(llm, prompt_loader).run(
        _input(content={"rows": [{"failures": 35}]})
    )

    assert output.ok


async def test_run_when_tool_failed_returns_not_ok_without_llm(
    prompt_loader: FilePromptLoader,
) -> None:
    llm = FakeLlmClient([])

    output = await StepReviewerAgent(llm, prompt_loader).run(_input(ok=False))

    assert not output.ok
    assert "no table" in output.feedback
    assert llm.calls == []
