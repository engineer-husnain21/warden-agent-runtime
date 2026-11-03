import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.clients.tool_client import ToolClient
from app.core.logging import get_logger
from app.models import RunStep
from app.orchestrators.agent_run_orchestrator import AgentRunOrchestrator
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.approval_repository import ApprovalRepository
from app.schemas.agent_run_metrics_response import AgentRunMetricsResponse
from app.schemas.agent_run_report_response import AgentRunReportResponse
from app.schemas.agent_run_response import AgentRunResponse
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.approval_decision import ApprovalDecision
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_response import RunStepResponse
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent
from app.schemas.step_metrics_response import StepMetricsResponse
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class AgentRunService:
    """Creates and executes runs, persists every step as it happens, and serves the results."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_service: AuditService,
        orchestrator: AgentRunOrchestrator,
        tool_client: ToolClient,
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_service
        self._orchestrator = orchestrator
        self._tool_client = tool_client
        self._background: set[asyncio.Task[None]] = set()

    async def create_run(self, task: str, caller: Caller) -> AgentRunResponse:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).create(task, caller.name, caller.role.value)
        await self._audit.record(
            actor=caller.name, role=caller.role.value, action=AuditAction.RUN_CREATED, run_id=run.id
        )
        return AgentRunResponse.model_validate(run)

    async def submit_run(self, task: str, caller: Caller) -> AgentRunResponse:
        """Create a run and execute it in the background (the API answers 202 right away)."""
        run = await self.create_run(task, caller)
        self._spawn(self.execute_run(run.id))
        return run

    async def execute_run(self, run_id: str) -> None:
        run = await self._set_status(run_id, AgentRunStatus.RUNNING)
        try:
            tools = await self._tool_client.list_tools()
        except Exception as error:
            await self._fail(run, error)
            return
        events = self._orchestrator.stream(run.id, run.task, Role(run.role), tools)
        await self._consume(run, events)

    async def resume_interrupted_runs(self) -> int:
        """At startup: continue runs that a crash or restart left `running` or `pending`.

        Runs with a checkpoint continue from it; runs that never saved state start fresh.
        Runs waiting for approval stay paused until a human decides.
        """
        resumed = 0
        for status in (AgentRunStatus.RUNNING, AgentRunStatus.PENDING):
            async with self._session_factory() as session:
                runs = await AgentRunRepository(session).list_by_status(status)
            for run in runs:
                if await self._orchestrator.has_checkpoint(run.id):
                    self.resume_in_background(run.id)
                else:
                    self._spawn(self.execute_run(run.id))
                resumed += 1
        if resumed:
            logger.info("Resuming %d interrupted run(s)", resumed)
        return resumed

    def resume_in_background(self, run_id: str, decision: ApprovalDecision | None = None) -> None:
        self._spawn(self.resume_run(run_id, decision))

    async def drain(self) -> None:
        """Wait until every background run task has finished (tests and shutdown)."""
        while self._background:
            await asyncio.gather(*self._background, return_exceptions=True)

    async def resume_run(self, run_id: str, decision: ApprovalDecision | None = None) -> None:
        """Continue a paused run with a decision, or a crashed one from its last checkpoint."""
        run = await self._set_status(run_id, AgentRunStatus.RUNNING)
        await self._consume(run, self._orchestrator.resume(run_id, decision))

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

    async def _consume(self, run: AgentRunResponse, events: AsyncIterator[StepEvent]) -> None:
        paused: StepEvent | None = None
        report: str | None = None
        try:
            async for event in events:
                await self._persist(event, run)
                if event.kind is RunStepKind.APPROVAL:
                    paused = event if event.status is RunStepStatus.AWAITING_APPROVAL else None
                if event.kind is RunStepKind.REPORT:
                    report = str((event.output or {}).get("report", ""))
        except Exception as error:
            await self._fail(run, error)
            return

        if paused is not None:
            await self._pause_for_approval(run, paused)
        elif report is not None:
            await self._set_status(run.id, AgentRunStatus.COMPLETED, report=report)
            await self._audit.record(
                actor=run.requested_by,
                role=run.role,
                action=AuditAction.RUN_COMPLETED,
                run_id=run.id,
            )
        else:
            await self._fail(run, RuntimeError("The run stopped without a report"))

    async def _persist(self, event: StepEvent, run: AgentRunResponse) -> None:
        step = RunStep(
            step_index=event.step_index,
            kind=event.kind,
            status=event.status,
            agent=event.agent,
            tool_name=event.tool_name,
            tool_arguments=event.tool_arguments,
            output=event.output,
            policy_decision=event.policy_decision.value if event.policy_decision else None,
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
            latency_ms=event.latency_ms,
            cost_usd=event.cost_usd,
        )
        async with self._session_factory() as session:
            await AgentRunRepository(session).add_step(run.id, step)
        await self._audit.record_event(event, actor=run.requested_by, role=run.role)

    async def _pause_for_approval(self, run: AgentRunResponse, event: StepEvent) -> None:
        async with self._session_factory() as session:
            await ApprovalRepository(session).create(
                run_id=run.id,
                step_position=event.step_index or 0,
                tool_name=event.tool_name or "",
                tool_arguments=event.tool_arguments or {},
                requested_by=run.requested_by,
            )
        await self._set_status(run.id, AgentRunStatus.AWAITING_APPROVAL)

    async def _fail(self, run: AgentRunResponse, error: Exception) -> None:
        logger.exception("Run %s failed", run.id, exc_info=error)
        message = f"{type(error).__name__}: {error}"[:1000]
        await self._set_status(run.id, AgentRunStatus.FAILED, error=message)
        await self._audit.record(
            actor=run.requested_by,
            role=run.role,
            action=AuditAction.RUN_FAILED,
            run_id=run.id,
            result={"error": message},
        )

    async def _set_status(
        self, run_id: str, status: AgentRunStatus, **fields: Any
    ) -> AgentRunResponse:
        async with self._session_factory() as session:
            run = await AgentRunRepository(session).update_status(run_id, status, **fields)
        return AgentRunResponse.model_validate(run)

    def _spawn(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(work)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
