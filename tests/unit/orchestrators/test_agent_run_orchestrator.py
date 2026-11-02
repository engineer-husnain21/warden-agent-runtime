from app.schemas.role import Role
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient
from tests.unit.orchestrators.orchestrator_helpers import (
    TOOLS,
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

    events = await collect(orchestrator.stream("run-1", "Book a flight", Role.OPERATOR, TOOLS))

    assert kinds(events) == [("plan", "succeeded"), ("report", "succeeded")]
    assert events[0].output == {"steps": []}
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

    events = await collect(build_orchestrator(llm, tools).stream("run-2", TASK, Role.VIEWER, TOOLS))

    step_events = [
        ("tool_selection", "succeeded"),
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

    events = await collect(build_orchestrator(llm, tools).stream("run-3", TASK, Role.ADMIN, TOOLS))

    assert kinds(events) == [
        ("plan", "succeeded"),
        ("tool_selection", "failed"),
        ("report", "succeeded"),
    ]
    assert tools.calls == []
    assert "[failed]" in llm.calls[-1][1].content
