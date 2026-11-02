from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.agent_run_repository import AgentRunRepository
from app.schemas.agent_run_metrics_response import AgentRunMetricsResponse
from app.schemas.agent_run_report_response import AgentRunReportResponse
from app.schemas.agent_run_response import AgentRunResponse
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.run_step_response import RunStepResponse
from app.schemas.step_metrics_response import StepMetricsResponse
from app.services.audit_service import AuditService


class AgentRunService:
    """Creates runs and serves their status, trace, report and metrics."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], audit_service: AuditService
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_service

    async def create_run(self, task: str, caller: Caller) -> AgentRunResponse:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).create(task, caller.name, caller.role.value)
        await self._audit.record(
            actor=caller.name, role=caller.role.value, action=AuditAction.RUN_CREATED, run_id=run.id
        )
        return AgentRunResponse.model_validate(run)

    async def get_run(self, run_id: str) -> AgentRunResponse:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).get_by_id(run_id)
        return AgentRunResponse.model_validate(run)

    async def list_runs(self, limit: int = 50) -> list[AgentRunResponse]:
        async with self._session_factory() as session:
            runs = await AgentRunRepository(session).list_recent(limit)
        return [AgentRunResponse.model_validate(run) for run in runs]

    async def get_steps(self, run_id: str) -> list[RunStepResponse]:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).get_by_id(run_id)
            return [RunStepResponse.model_validate(step) for step in run.steps]

    async def get_report(self, run_id: str) -> AgentRunReportResponse:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).get_by_id(run_id)
        return AgentRunReportResponse(run_id=run.id, status=run.status, report=run.report)

    async def get_metrics(self, run_id: str) -> AgentRunMetricsResponse:
        steps = [StepMetricsResponse.model_validate(s) for s in await self.get_steps(run_id)]
        return AgentRunMetricsResponse(
            run_id=run_id,
            steps=steps,
            llm_calls=sum(1 for s in steps if s.input_tokens or s.output_tokens),
            total_input_tokens=sum(s.input_tokens for s in steps),
            total_output_tokens=sum(s.output_tokens for s in steps),
            total_latency_ms=sum(s.latency_ms for s in steps),
            total_cost_usd=sum(s.cost_usd for s in steps),
        )
