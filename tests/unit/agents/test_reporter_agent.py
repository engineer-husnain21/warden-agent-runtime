import pytest

from app.agents.reporter_agent import ReporterAgent
from app.core.dependencies import PROMPTS_DIR
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
    assert "Steps not done: 1" in user_message


async def test_run_when_every_step_succeeded_tells_model_nothing_was_skipped(
    prompt_loader: FilePromptLoader,
) -> None:
    llm = FakeLlmClient(["## Summary\nAll done."])

    await ReporterAgent(llm, prompt_loader).run(ReporterInput(task="t", steps=STEPS[:1]))

    assert "Steps not done: 0" in llm.calls[0][1].content


async def test_run_when_reply_blank_raises_agent_output_error(
    prompt_loader: FilePromptLoader,
) -> None:
    with pytest.raises(AgentOutputError):
        await ReporterAgent(FakeLlmClient(["   "]), prompt_loader).run(
            ReporterInput(task="t", steps=[])
        )


DRY_RUN_STEP = StepRecord(
    description="Open an issue for the top causes",
    outcome="succeeded",
    tool="github.create_issue",
    result=ToolResult(
        tool="github.create_issue",
        ok=True,
        content={"issue": {"number": 1000, "url": None, "dry_run": True}},
    ),
)


async def test_run_when_issue_is_dry_run_removes_links_to_it(
    prompt_loader: FilePromptLoader,
) -> None:
    reply = (
        "## Actions taken\n"
        "- [Issue #1000](https://github.com/octo/warden-sandbox/issues/1000)\n"
        "- Also see https://github.com/octo/warden-sandbox/issues/1000\n"
        "- Older issue https://github.com/octo/warden-sandbox/issues/12 stays linked"
    )
    llm = FakeLlmClient([reply])

    output = await ReporterAgent(llm, prompt_loader).run(
        ReporterInput(task="t", steps=[DRY_RUN_STEP])
    )

    assert "issues/1000" not in output.report
    assert "- Issue #1000 (dry-run, not created)" in output.report
    assert "- Also see (dry-run, not created)" in output.report
    assert "https://github.com/octo/warden-sandbox/issues/12" in output.report


async def test_run_when_issue_is_live_keeps_its_link(prompt_loader: FilePromptLoader) -> None:
    live_step = DRY_RUN_STEP.model_copy(
        update={
            "result": ToolResult(
                tool="github.create_issue",
                ok=True,
                content={"issue": {"number": 7, "url": "https://github.com/o/r/issues/7"}},
            )
        }
    )
    reply = "- [Issue #7](https://github.com/o/r/issues/7)"

    output = await ReporterAgent(FakeLlmClient([reply]), prompt_loader).run(
        ReporterInput(task="t", steps=[live_step])
    )

    assert output.report == reply


def test_reporter_prompt_when_loaded_forbids_dry_run_links() -> None:
    prompt = (PROMPTS_DIR / "reporter_system.md").read_text(encoding="utf-8")

    assert "(dry-run, not created)" in prompt
