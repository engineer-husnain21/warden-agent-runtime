import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import get_audit_service
from app.routers import audit_log_router
from app.schemas.audit_action import AuditAction
from app.services.audit_service import AuditService
from tests.unit.routers.router_helpers import build_client


@pytest.fixture
async def audit(session_factory: async_sessionmaker[AsyncSession]) -> AuditService:
    service = AuditService(session_factory)
    await service.record(
        actor="oscar", role="operator", action=AuditAction.RUN_CREATED, run_id="r1"
    )
    await service.record(actor="vera", role="viewer", action=AuditAction.RUN_CREATED, run_id="r2")
    return service


def _client(audit: AuditService, key: str) -> AsyncClient:
    return build_client([audit_log_router.router], {get_audit_service: lambda: audit}, key)


async def test_get_audit_log_when_admin_returns_entries(audit: AuditService) -> None:
    async with _client(audit, "admin-key") as client:
        response = await client.get("/api/v1/audit-log-entries", params={"run_id": "r1"})

    assert response.status_code == 200
    assert [(e["actor"], e["action"]) for e in response.json()] == [("oscar", "run_created")]


async def test_get_audit_log_when_operator_returns_403(audit: AuditService) -> None:
    async with _client(audit, "operator-key") as client:
        response = await client.get("/api/v1/audit-log-entries")

    assert response.status_code == 403
