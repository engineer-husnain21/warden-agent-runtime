from collections.abc import Sequence

from sqlalchemy import func, select

from app.db.base import utc_now
from app.models import AgentRun, AgentRunStatus, RunStep
from app.repositories.base_repository import BaseRepository

_TERMINAL_STATUSES = {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED}


class AgentRunRepository(BaseRepository[AgentRun]):
    model = AgentRun

    async def create(self, task: str, requested_by: str, role: str) -> AgentRun:
        return await self._save(AgentRun(task=task, requested_by=requested_by, role=role))

    async def list_recent(self, limit: int = 50) -> Sequence[AgentRun]:
        query = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
        return (await self._session.scalars(query)).all()

    async def list_by_status(self, status: AgentRunStatus) -> Sequence[AgentRun]:
        query = select(AgentRun).where(AgentRun.status == status).order_by(AgentRun.created_at)
        return (await self._session.scalars(query)).all()

    async def update_status(
        self,
        run_id: str,
        status: AgentRunStatus,
        *,
        report: str | None = None,
        error: str | None = None,
    ) -> AgentRun:
        run = await self.get_by_id(run_id)
        run.status = status
        if report is not None:
            run.report = report
        if error is not None:
            run.error = error
        if status in _TERMINAL_STATUSES:
            run.completed_at = utc_now()
        return await self._save(run)

    async def add_step(self, run_id: str, step: RunStep) -> RunStep:
        """Append a step to the run; its position is assigned here (0, 1, 2, ...)."""
        count_query = select(func.count()).where(RunStep.run_id == run_id)
        step.run_id = run_id
        step.position = await self._session.scalar(count_query) or 0
        self._session.add(step)
        await self._session.commit()
        await self._session.refresh(step)
        return step
