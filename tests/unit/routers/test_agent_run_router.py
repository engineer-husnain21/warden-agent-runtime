from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.dependencies import get_agent_run_service
from app.core.exceptions import NotFoundError
from app.routers import agent_run_router
from app.schemas.agent_run_metrics_response import AgentRunMetricsResponse
from app.schemas.agent_run_response import AgentRunResponse
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.caller import Caller
from tests.unit.routers.router_helpers import build_client

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _run(run_id: str = "r1", status: AgentRunStatus = AgentRunStatus.PENDING) -> AgentRunResponse:
    return AgentRunResponse(
        id=run_id,
        task="Find failed orders",
        requested_by="oscar",
        role="operator",
        status=status,
        error=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )


class _FakeRunService:
    def __init__(self) -> None:
        self.submitted: list[tuple[str, Caller]] = []

    async def submit_run(self, task: str, caller: Caller) -> AgentRunResponse:
        self.submitted.append((task, caller))
        return _run()

    async def get_run(self, run_id: str) -> AgentRunResponse:
        if run_id != "r1":
            raise NotFoundError(f"AgentRun {run_id} not found")
        return _run(status=AgentRunStatus.COMPLETED)

    async def get_metrics(self, run_id: str) -> AgentRunMetricsResponse:
        return AgentRunMetricsResponse(
            run_id=run_id,
            steps=[],
            llm_calls=5,
            total_input_tokens=4000,
            total_output_tokens=2000,
            total_latency_ms=6200.0,
            total_cost_usd=0.0016,
        )


def _client(service: _FakeRunService, key: str = "operator-key") -> AsyncClient:
    return build_client([agent_run_router.router], {get_agent_run_service: lambda: service}, key)


async def test_post_agent_runs_when_valid_returns_202() -> None:
    service = _FakeRunService()
    async with _client(service) as client:
        response = await client.post("/api/v1/agent-runs", json={"task": "Find failed orders"})

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    [(task, caller)] = service.submitted
    assert (task, caller.name, caller.role.value) == ("Find failed orders", "oscar", "operator")


async def test_post_agent_runs_when_task_too_short_returns_422() -> None:
    async with _client(_FakeRunService()) as client:
        response = await client.post("/api/v1/agent-runs", json={"task": "x"})

    assert response.status_code == 422


async def test_get_agent_run_when_unknown_returns_404_json_error() -> None:
    async with _client(_FakeRunService()) as client:
        response = await client.get("/api/v1/agent-runs/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_get_metrics_when_run_exists_returns_totals() -> None:
    async with _client(_FakeRunService(), key="viewer-key") as client:
        response = await client.get("/api/v1/agent-runs/r1/metrics")

    assert response.status_code == 200
    assert response.json()["total_cost_usd"] == 0.0016


async def test_post_agent_runs_when_no_key_returns_401() -> None:
    async with _client(_FakeRunService(), key="") as client:
        response = await client.post("/api/v1/agent-runs", json={"task": "Find failed orders"})

    assert response.status_code == 401
