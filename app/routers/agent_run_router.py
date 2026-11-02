from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_agent_run_service, get_current_caller
from app.schemas.agent_run_metrics_response import AgentRunMetricsResponse
from app.schemas.agent_run_report_response import AgentRunReportResponse
from app.schemas.agent_run_response import AgentRunResponse
from app.schemas.caller import Caller
from app.schemas.create_agent_run_request import CreateAgentRunRequest
from app.schemas.run_step_response import RunStepResponse
from app.services.agent_run_service import AgentRunService

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])

RunService = Annotated[AgentRunService, Depends(get_agent_run_service)]
CurrentCaller = Annotated[Caller, Depends(get_current_caller)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_agent_run(
    body: CreateAgentRunRequest, caller: CurrentCaller, service: RunService
) -> AgentRunResponse:
    """Submit a task. The run executes in the background; poll it with GET."""
    return await service.submit_run(body.task, caller)


@router.get("")
async def list_agent_runs(
    _caller: CurrentCaller, service: RunService, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[AgentRunResponse]:
    return await service.list_runs(limit)


@router.get("/{run_id}")
async def get_agent_run(
    run_id: str, _caller: CurrentCaller, service: RunService
) -> AgentRunResponse:
    return await service.get_run(run_id)


@router.get("/{run_id}/steps")
async def get_agent_run_steps(
    run_id: str, _caller: CurrentCaller, service: RunService
) -> list[RunStepResponse]:
    return await service.get_steps(run_id)


@router.get("/{run_id}/report")
async def get_agent_run_report(
    run_id: str, _caller: CurrentCaller, service: RunService
) -> AgentRunReportResponse:
    return await service.get_report(run_id)


@router.get("/{run_id}/metrics")
async def get_agent_run_metrics(
    run_id: str, _caller: CurrentCaller, service: RunService
) -> AgentRunMetricsResponse:
    return await service.get_metrics(run_id)
