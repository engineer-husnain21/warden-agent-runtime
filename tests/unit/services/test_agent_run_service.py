import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import NotFoundError
from app.models import RunStep
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.approval_repository import ApprovalRepository
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.services.agent_run_service import AgentRunService
from app.services.audit_service import AuditService
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient
from tests.unit.orchestrators.orchestrator_helpers import (
    TOOLS,
    build_orchestrator,
    plan,
    review,
    select,
)

OSCAR = Caller(name="oscar", role=Role.OPERATOR)
ADA = Caller(name="ada", role=Role.ADMIN)


@pytest.fixture
def audit(session_factory: async_sessionmaker[AsyncSession]) -> AuditService:
    return AuditService(session_factory)


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    audit: AuditService,
    llm_replies: list[str] | None = None,
    tools: FakeToolClient | None = None,
) -> AgentRunService:
    tools = tools or FakeToolClient(tools=TOOLS)
    orchestrator = build_orchestrator(FakeLlmClient(llm_replies or []), tools)
    return AgentRunService(session_factory, audit, orchestrator, tools)


@pytest.fixture
def service(
    session_factory: async_sessionmaker[AsyncSession], audit: AuditService
) -> AgentRunService:
    return _service(session_factory, audit)


async def test_create_run_when_valid_persists_pending_run(
    service: AgentRunService, audit: AuditService
) -> None:
    created = await service.create_run("Find failed orders", OSCAR)

    loaded = await service.get_run(created.id)

    assert loaded.status is AgentRunStatus.PENDING
    assert (loaded.requested_by, loaded.role) == ("oscar", "operator")
    [entry] = await audit.list_entries(ADA)
    assert (entry.action, entry.run_id) == (AuditAction.RUN_CREATED, created.id)


async def test_get_run_when_missing_raises_not_found(service: AgentRunService) -> None:
    with pytest.raises(NotFoundError):
        await service.get_run("nope")


async def test_get_metrics_when_steps_have_usage_sums_them(
    service: AgentRunService, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    run = await service.create_run("task", OSCAR)
    async with session_factory() as session:
        repository = AgentRunRepository(session)
        for kind, tokens, cost in [
            (RunStepKind.PLAN, (600, 400), 0.0003),
            (RunStepKind.TOOL_CALL, (0, 0), 0.0),
            (RunStepKind.REPORT, (640, 470), 0.0004),
        ]:
            step = RunStep(
                kind=kind,
                status=RunStepStatus.SUCCEEDED,
                input_tokens=tokens[0],
                output_tokens=tokens[1],
                latency_ms=1000.0 if tokens[0] else 0.0,
                cost_usd=cost,
            )
            await repository.add_step(run.id, step)

    metrics = await service.get_metrics(run.id)

    assert metrics.llm_calls == 2
    assert (metrics.total_input_tokens, metrics.total_output_tokens) == (1240, 870)
    assert metrics.total_latency_ms == 2000.0
    assert metrics.total_cost_usd == pytest.approx(0.0007)
    assert [s.kind for s in metrics.steps] == [
        RunStepKind.PLAN,
        RunStepKind.TOOL_CALL,
        RunStepKind.REPORT,
    ]


async def test_get_report_when_run_not_finished_returns_null_report(
    service: AgentRunService,
) -> None:
    run = await service.create_run("task", OSCAR)

    report = await service.get_report(run.id)

    assert report.report is None
    assert report.status is AgentRunStatus.PENDING


async def test_execute_when_events_streamed_persists_each_step_and_audit(
    session_factory: async_sessionmaker[AsyncSession], audit: AuditService
) -> None:
    replies = [
        plan("Count failed orders"),
        select("warehouse.run_query", sql="SELECT COUNT(*) AS n FROM orders"),
        review(True),
        "## Summary\n35 orders failed.",
    ]
    tools = FakeToolClient(tools=TOOLS, results={"warehouse.run_query": {"rows": [{"n": 35}]}})
    service = _service(session_factory, audit, replies, tools)
    run = await service.create_run("Count failed orders", ADA)

    await service.execute_run(run.id)

    steps = await service.get_steps(run.id)
    assert [s.kind.value for s in steps] == [
        "plan",
        "tool_selection",
        "permission_check",
        "tool_call",
        "review",
        "report",
    ]
    assert steps[0].input_tokens > 0
    finished = await service.get_report(run.id)
    assert finished.status is AgentRunStatus.COMPLETED
    assert finished.report == "## Summary\n35 orders failed."
    actions = [e.action for e in await audit.list_entries(ADA, run_id=run.id)]
    assert actions == [
        AuditAction.RUN_CREATED,
        AuditAction.TOOL_CALL_ALLOWED,
        AuditAction.TOOL_CALL_SUCCEEDED,
        AuditAction.RUN_COMPLETED,
    ]


async def test_execute_when_tool_needs_approval_pauses_and_creates_approval(
    session_factory: async_sessionmaker[AsyncSession], audit: AuditService
) -> None:
    replies = [plan("Open an issue"), select("github.create_issue", title="Timeouts")]
    service = _service(session_factory, audit, replies)
    run = await service.create_run("Open an issue", OSCAR)

    await service.execute_run(run.id)

    assert (await service.get_run(run.id)).status is AgentRunStatus.AWAITING_APPROVAL
    async with session_factory() as session:
        pending = await ApprovalRepository(session).get_pending_for_run(run.id)
    assert pending is not None
    assert (pending.tool_name, pending.tool_arguments) == (
        "github.create_issue",
        {"title": "Timeouts"},
    )
    assert AuditAction.APPROVAL_REQUESTED in [
        e.action for e in await audit.list_entries(ADA, run_id=run.id)
    ]


async def test_execute_when_orchestrator_crashes_marks_run_failed(
    session_factory: async_sessionmaker[AsyncSession], audit: AuditService
) -> None:
    service = _service(session_factory, audit, llm_replies=[])  # the planner gets no reply
    run = await service.create_run("task", OSCAR)

    await service.execute_run(run.id)

    failed = await service.get_run(run.id)
    assert failed.status is AgentRunStatus.FAILED
    assert failed.error is not None
    assert "AssertionError" in failed.error
