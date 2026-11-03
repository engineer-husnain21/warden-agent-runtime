"""Full request flow through the real app: auth, routers, services, orchestrator, DB.

The LLM and the tools are fakes so the test is fast and deterministic; everything else is real.
"""

import json
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.dependencies import get_agent_run_service, get_approval_service, get_audit_service
from app.main import create_app
from app.middlewares.api_key_auth_middleware import API_KEY_HEADER
from app.services.agent_run_service import AgentRunService
from app.services.approval_service import ApprovalService
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

TASK = "Find orders that failed in the last 24 hours and open a GitHub issue for the top 3 causes"
KEYS = {"operator-key": ("oscar", "operator"), "admin-key": ("ada", "admin")}


@pytest.fixture(autouse=True)
def _api_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    keys = {key: {"name": name, "role": role} for key, (name, role) in KEYS.items()}
    monkeypatch.setenv("API_KEYS", json.dumps(keys))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def setup(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[tuple[AsyncClient, AgentRunService, FakeToolClient]]:
    replies = [
        plan("Count failed orders in the last 24h by failure_reason", "Open one issue"),
        select("warehouse.run_query", sql="SELECT failure_reason, COUNT(*) AS n FROM orders"),
        review(True),
        select("github.create_issue", title="Top 3 failure causes"),
        review(True),
        "## Summary\nTop cause payment_timeout (14). Opened issue #1000.",
    ]
    tools = FakeToolClient(
        tools=TOOLS,
        results={
            "warehouse.run_query": {"rows": [{"failure_reason": "payment_timeout", "n": 14}]},
            "github.create_issue": {"issue": {"number": 1000, "dry_run": True}},
        },
    )
    audit = AuditService(session_factory)
    runs = AgentRunService(
        session_factory, audit, build_orchestrator(FakeLlmClient(replies), tools)
    )
    app = create_app()
    app.dependency_overrides[get_audit_service] = lambda: audit
    app.dependency_overrides[get_agent_run_service] = lambda: runs
    app.dependency_overrides[get_approval_service] = lambda: ApprovalService(session_factory, runs)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, runs, tools


def _as(key: str) -> dict[str, str]:
    return {API_KEY_HEADER: key}


async def test_run_when_approved_completes_with_report_and_audit(
    setup: tuple[AsyncClient, AgentRunService, FakeToolClient],
) -> None:
    client, runs, tools = setup

    created = await client.post(
        "/api/v1/agent-runs", json={"task": TASK}, headers=_as("operator-key")
    )
    assert created.status_code == 202
    run_id = created.json()["id"]
    await runs.drain()

    paused = (await client.get(f"/api/v1/agent-runs/{run_id}", headers=_as("operator-key"))).json()
    assert paused["status"] == "awaiting_approval"
    [approval] = (await client.get("/api/v1/approvals", headers=_as("admin-key"))).json()
    assert approval["tool_name"] == "github.create_issue"
    assert tools.calls[-1].tool == "warehouse.run_query"  # the issue was not created yet

    decided = await client.post(
        f"/api/v1/approvals/{approval['id']}/decisions",
        json={"approved": True},
        headers=_as("admin-key"),
    )
    assert decided.status_code == 200
    await runs.drain()

    report = (
        await client.get(f"/api/v1/agent-runs/{run_id}/report", headers=_as("operator-key"))
    ).json()
    assert report["status"] == "completed"
    assert "payment_timeout" in report["report"]
    steps = (
        await client.get(f"/api/v1/agent-runs/{run_id}/steps", headers=_as("operator-key"))
    ).json()
    assert [s["kind"] for s in steps].count("tool_call") == 2
    metrics = (
        await client.get(f"/api/v1/agent-runs/{run_id}/metrics", headers=_as("operator-key"))
    ).json()
    assert metrics["llm_calls"] == 6
    assert metrics["total_input_tokens"] > 0

    audit = await client.get(
        "/api/v1/audit-log-entries", params={"run_id": run_id}, headers=_as("admin-key")
    )
    actions = [entry["action"] for entry in audit.json()]
    assert actions == [
        "run_created",
        "tool_call_allowed",
        "tool_call_succeeded",
        "approval_requested",
        "approval_granted",
        "tool_call_succeeded",
        "run_completed",
    ]
    assert (
        await client.get("/api/v1/audit-log-entries", headers=_as("operator-key"))
    ).status_code == 403
