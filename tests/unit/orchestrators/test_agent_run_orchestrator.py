from app.orchestrators.agent_run_orchestrator import AgentRunOrchestrator
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

TASK = "Count failed orders and list open issues"


async def test_stream_when_plan_has_no_steps_yields_report_event() -> None:
    llm = FakeLlmClient(['{"steps": []}', "## Summary\nNothing could be done."])
    orchestrator = build_orchestrator(llm)

    events = await collect(orchestrator.stream("run-1", "Book a flight", Role.OPERATOR))

    assert kinds(events) == [("plan", "succeeded"), ("report", "succeeded")]
    assert events[0].output == {"steps": [], "dropped_steps": 0}
    assert events[1].output == {"report": "## Summary\nNothing could be done."}
    assert all(event.run_id == "run-1" for event in events)


async def test_stream_when_two_steps_yields_events_in_order() -> None:
    llm = FakeLlmClient(
        [
            plan("Count failed orders", "Count all orders"),
            select(
                "warehouse.run_query", sql="SELECT COUNT(*) AS n FROM orders WHERE status='failed'"
            ),
            review(True),
            select("warehouse.run_query", sql="SELECT COUNT(*) AS n FROM orders"),
            review(True),
            "## Summary\n35 of 500 orders failed.",
        ]
    )
    tools = FakeToolClient(results={"warehouse.run_query": {"rows": [{"n": 35}]}})

    events = await collect(build_orchestrator(llm, tools).stream("run-2", TASK, Role.VIEWER))

    step_events = [
        ("tool_selection", "succeeded"),
        ("permission_check", "succeeded"),
        ("tool_call", "succeeded"),
        ("review", "succeeded"),
    ]
    assert kinds(events) == [
        ("plan", "succeeded"),
        *step_events,
        *step_events,
        ("report", "succeeded"),
    ]
    assert [e.step_index for e in events if e.kind.value == "tool_call"] == [0, 1]
    assert len(tools.calls) == 2
    # The second selection sees the first step's result.
    assert "step 1 (warehouse.run_query)" in llm.calls[3][1].content


async def test_stream_when_selector_fails_twice_records_failed_step_and_continues() -> None:
    bad = select("shell.run", cmd="ls")
    llm = FakeLlmClient([plan("Do something odd"), bad, bad, "## Summary\nThe step failed."])
    tools = FakeToolClient()

    events = await collect(build_orchestrator(llm, tools).stream("run-3", TASK, Role.ADMIN))

    assert kinds(events) == [
        ("plan", "succeeded"),
        ("tool_selection", "failed"),
        ("report", "succeeded"),
    ]
    assert tools.calls == []
    assert "[failed]" in llm.calls[-1][1].content


async def test_stream_when_viewer_creates_issue_yields_denied_event() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Payment timeouts"),
            "## Summary\nNo issue was opened: not allowed.",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1}}})

    events = await collect(build_orchestrator(llm, tools).stream("run-4", TASK, Role.VIEWER))

    assert kinds(events) == [
        ("plan", "succeeded"),
        ("tool_selection", "succeeded"),
        ("permission_check", "denied"),
        ("report", "succeeded"),
    ]
    assert events[2].policy_decision is not None
    assert events[2].policy_decision.value == "deny"
    assert tools.calls == []
    assert "[denied]" in llm.calls[-1][1].content
    assert "role 'viewer' may not call github.create_issue" in llm.calls[-1][1].content


async def test_stream_when_admin_creates_issue_executes_it() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Payment timeouts"),
            review(True),
            "## Summary\nOpened issue #1.",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1}}})

    events = await collect(build_orchestrator(llm, tools).stream("run-5", TASK, Role.ADMIN))

    assert ("tool_call", "succeeded") in kinds(events)
    assert len(tools.calls) == 1


async def test_stream_when_operator_creates_issue_pauses_awaiting_approval() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1}}})

    events = await collect(build_orchestrator(llm, tools).stream("run-6", TASK, Role.OPERATOR))

    assert kinds(events) == [
        ("plan", "succeeded"),
        ("tool_selection", "succeeded"),
        ("permission_check", "awaiting_approval"),
        ("approval", "awaiting_approval"),
    ]
    paused = events[-1]
    assert paused.tool_name == "github.create_issue"
    assert paused.tool_arguments == {"title": "Timeouts"}
    assert paused.step_index == 0
    assert tools.calls == []


async def _paused_run(llm: FakeLlmClient, tools: FakeToolClient) -> AgentRunOrchestrator:
    orchestrator = build_orchestrator(llm, tools)
    await collect(orchestrator.stream("run-7", TASK, Role.OPERATOR))
    return orchestrator


async def test_resume_when_approved_executes_tool_and_reports() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
            review(True),
            "## Summary\nOpened issue #1.",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1}}})
    orchestrator = await _paused_run(llm, tools)

    events = await collect(
        orchestrator.resume("run-7", ApprovalDecision(approved=True, decided_by="ada"))
    )

    assert kinds(events) == [
        ("approval", "succeeded"),
        ("tool_call", "succeeded"),
        ("review", "succeeded"),
        ("report", "succeeded"),
    ]
    assert events[0].output == {"approved": True, "decided_by": "ada", "reason": None}
    assert len(tools.calls) == 1


async def test_resume_when_rejected_skips_tool_and_continues() -> None:
    llm = FakeLlmClient(
        [
            plan("Open an issue for payment timeouts"),
            select("github.create_issue", title="Timeouts"),
            "## Summary\nNo issue was opened: rejected.",
        ]
    )
    tools = FakeToolClient(results={"github.create_issue": {"issue": {"number": 1}}})
    orchestrator = await _paused_run(llm, tools)

    events = await collect(
        orchestrator.resume(
            "run-7", ApprovalDecision(approved=False, decided_by="ada", reason="duplicate")
        )
    )

    assert kinds(events) == [("approval", "denied"), ("report", "succeeded")]
    assert tools.calls == []
    assert "Rejected by ada: duplicate" in llm.calls[-1][1].content


async def test_stream_when_llm_used_events_carry_usage() -> None:
    llm = FakeLlmClient(
        [
            plan("Count failed orders"),
            select("warehouse.run_query", sql="SELECT COUNT(*) FROM orders"),
            review(True),
            "## Summary\nDone.",
        ]
    )
    tools = FakeToolClient(results={"warehouse.run_query": {"rows": [{"n": 35}]}})

    events = await collect(build_orchestrator(llm, tools).stream("run-8", TASK, Role.ADMIN))

    by_kind = {event.kind.value: event for event in events}
    for kind in ("plan", "tool_selection", "review", "report"):
        assert len(by_kind[kind].usage) == 1
        assert by_kind[kind].input_tokens > 0
        assert by_kind[kind].output_tokens > 0
        assert by_kind[kind].latency_ms == 1.0
    assert by_kind["tool_call"].usage == []
    assert by_kind["permission_check"].cost_usd == 0.0


async def test_stream_when_review_fails_twice_marks_step_failed() -> None:
    llm = FakeLlmClient(
        [
            plan("Count failed orders"),
            select("warehouse.run_query", sql="SELECT * FROM orders WHERE 0"),
            review(False, "No rows; filter on status = 'failed'."),
            select("warehouse.run_query", sql="SELECT * FROM orders WHERE 1 = 0"),
            review(False, "Still no rows."),
            "## Summary\nThe step failed.",
        ]
    )
    tools = FakeToolClient(results={"warehouse.run_query": {"rows": []}})

    events = await collect(build_orchestrator(llm, tools).stream("run-9", TASK, Role.ADMIN))

    assert [e.status.value for e in events if e.kind.value == "review"] == ["failed", "failed"]
    assert len(tools.calls) == 2
    assert "No rows; filter on status = 'failed'." in llm.calls[3][1].content
    assert "Count failed orders [failed]" in llm.calls[-1][1].content


async def test_stream_when_review_fails_once_then_passes_succeeds() -> None:
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

    await collect(build_orchestrator(llm, tools).stream("run-10", TASK, Role.ADMIN))

    assert "Count failed orders [succeeded]" in llm.calls[-1][1].content


async def test_stream_when_plan_too_long_keeps_first_max_steps() -> None:
    llm = FakeLlmClient([plan("a", "b", "c"), "x", "y", "z"])
    orchestrator = build_orchestrator(llm, max_steps=0)

    events = await collect(orchestrator.stream("run-11", TASK, Role.ADMIN))

    assert events[0].output == {"steps": [], "dropped_steps": 3}
    assert kinds(events)[-1] == ("report", "succeeded")


async def test_has_checkpoint_when_run_started_is_true_and_unknown_run_false() -> None:
    llm = FakeLlmClient(['{"steps": []}', "## Summary\nDone."])
    orchestrator = build_orchestrator(llm)
    await collect(orchestrator.stream("run-12", TASK, Role.ADMIN))

    assert await orchestrator.has_checkpoint("run-12")
    assert not await orchestrator.has_checkpoint("never-started")
