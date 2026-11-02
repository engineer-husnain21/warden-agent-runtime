from app.schemas.role import Role
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.unit.orchestrators.orchestrator_helpers import TOOLS, build_orchestrator, collect, kinds


async def test_stream_when_plan_has_no_steps_yields_report_event() -> None:
    llm = FakeLlmClient(['{"steps": []}', "## Summary\nNothing could be done."])
    orchestrator = build_orchestrator(llm)

    events = await collect(orchestrator.stream("run-1", "Book a flight", Role.OPERATOR, TOOLS))

    assert kinds(events) == [("plan", "succeeded"), ("report", "succeeded")]
    assert events[0].output == {"steps": []}
    assert events[1].output == {"report": "## Summary\nNothing could be done."}
    assert all(event.run_id == "run-1" for event in events)
