import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import NotFoundError
from app.models import RunStep
from app.repositories.agent_run_repository import AgentRunRepository
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.services.agent_run_service import AgentRunService
from app.services.audit_service import AuditService

OSCAR = Caller(name="oscar", role=Role.OPERATOR)
ADA = Caller(name="ada", role=Role.ADMIN)


@pytest.fixture
def audit(session_factory: async_sessionmaker[AsyncSession]) -> AuditService:
    return AuditService(session_factory)


@pytest.fixture
def service(
    session_factory: async_sessionmaker[AsyncSession], audit: AuditService
) -> AgentRunService:
    return AgentRunService(session_factory, audit)


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
