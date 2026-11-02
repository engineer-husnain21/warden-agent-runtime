import pytest

from app.agents.reporter_agent import ReporterAgent
from app.core.exceptions import AgentOutputError
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.reporter_input import ReporterInput
from app.schemas.agents.step_record import StepRecord
from app.schemas.tool_result import ToolResult
from tests.fakes.fake_llm_client import FakeLlmClient

STEPS = [
    StepRecord(
        description="Count failed orders by reason",
        outcome="succeeded",
        tool="warehouse.run_query",
        result=ToolResult(
            tool="warehouse.run_query",
            ok=True,
            content={"rows": [{"failure_reason": "payment_timeout", "failures": 14}]},
        ),
    ),
    StepRecord(
        description="Open an issue for the top cause",
        outcome="rejected",
        tool="github.create_issue",
        note="Rejected by ada: duplicate of #12",
    ),
]


async def test_run_when_steps_given_returns_markdown_report(
    prompt_loader: FilePromptLoader,
) -> None:
    llm = FakeLlmClient(["## Summary\nFound 14 payment timeouts. No issue was opened.\n"])

    output = await ReporterAgent(llm, prompt_loader).run(
        ReporterInput(task="Report failed orders", steps=STEPS)
    )

    assert output.report.startswith("## Summary")
    assert len(output.usage) == 1
    user_message = llm.calls[0][1].content
    assert "1. Count failed orders by reason [succeeded]" in user_message
    assert '"failures": 14' in user_message
    assert "2. Open an issue for the top cause [rejected]" in user_message
    assert "note: Rejected by ada: duplicate of #12" in user_message


async def test_run_when_reply_blank_raises_agent_output_error(
    prompt_loader: FilePromptLoader,
) -> None:
    with pytest.raises(AgentOutputError):
        await ReporterAgent(FakeLlmClient(["   "]), prompt_loader).run(
            ReporterInput(task="t", steps=[])
        )
