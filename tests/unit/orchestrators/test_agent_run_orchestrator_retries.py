"""Step retries after a rejected review: reads may run again, a write that ran never does."""

from app.schemas.approval_decision import ApprovalDecision
from app.schemas.role import Role
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

TASK = "Count failed orders and open an issue"
DRY_RUN_FEEDBACK = "The issue was not actually created (dry_run: true)."


async def test_resume_when_reviewer_rejects_approved_create_issue_never_repeats_it() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
            review(False, DRY_RUN_FEEDBACK),
            "## Summary\nOpened issue #1000 (dry-run).",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1000}}})
    orchestrator = build_orchestrator(llm, tools)
    await collect(orchestrator.stream("run-w1", TASK, Role.OPERATOR))

    events = await collect(
        orchestrator.resume("run-w1", ApprovalDecision(approved=True, decided_by="ada"))
    )

    assert kinds(events) == [
        ("approval", "succeeded"),
        ("tool_call", "succeeded"),
        ("review", "succeeded"),
        ("report", "succeeded"),
    ]
    assert len(tools.calls) == 1  # no second tool call ...
    assert not any(e.status.value == "awaiting_approval" for e in events)  # ... and no 2nd approval
    review_event = next(e for e in events if e.kind.value == "review")
    assert review_event.output is not None
    assert review_event.output["ok"] is False
    assert "not repeated" in review_event.output["warning"]
    report_prompt = llm.calls[-1][1].content
    assert "Open an issue for payment timeouts [succeeded]" in report_prompt
    assert f"Reviewer warning: {DRY_RUN_FEEDBACK}" in report_prompt


async def test_stream_when_reviewer_rejects_admin_write_without_approval_never_repeats_it() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
            review(False, DRY_RUN_FEEDBACK),
            "## Summary\nOpened issue #1000 (dry-run).",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1000}}})

    events = await collect(build_orchestrator(llm, tools).stream("run-w2", TASK, Role.ADMIN))

    assert len(tools.calls) == 1
    assert [e.status.value for e in events if e.kind.value == "review"] == ["succeeded"]


async def test_stream_when_reviewer_rejects_read_only_step_retries_it_once() -> None:
    llm = FakeLlmClient(
        [
            plan("Count failed orders"),
            select("warehouse.run_query", sql="SELECT 0"),
            review(False, "Wrong query."),
            select("warehouse.run_query", sql="SELECT COUNT(*) FROM orders WHERE status='failed'"),
            review(True),
            "## Summary\n35 failed orders.",
        ]
    )
    tools = FakeToolClient(results={"warehouse.run_query": {"rows": [{"n": 35}]}})

    events = await collect(build_orchestrator(llm, tools).stream("run-w3", TASK, Role.OPERATOR))

    assert len(tools.calls) == 2
    assert [e.status.value for e in events if e.kind.value == "review"] == ["failed", "succeeded"]
    assert "Wrong query." in llm.calls[3][1].content  # the retry's selector got the feedback


async def test_stream_when_write_call_failed_retries_it_once() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
            select("github.create_issue", title="Timeouts"),
            "## Summary\nThe issue could not be opened.",
        ]
    )
    tools = FakeToolClient(errors={"github.create_issue": "GitHub API returned 502"})

    events = await collect(build_orchestrator(llm, tools).stream("run-w4", TASK, Role.ADMIN))

    assert len(tools.calls) == 2  # nothing was created, so a retry is safe
    assert [e.status.value for e in events if e.kind.value == "review"] == ["failed", "failed"]
