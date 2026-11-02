from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.dependencies import get_approval_service
from app.core.exceptions import PermissionDeniedError
from app.routers import approval_router
from app.schemas.approval_decision_request import ApprovalDecisionRequest
from app.schemas.approval_response import ApprovalResponse
from app.schemas.approval_status import ApprovalStatus
from app.schemas.caller import Caller
from app.schemas.role import Role
from tests.unit.routers.router_helpers import build_client

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _approval(status: ApprovalStatus = ApprovalStatus.PENDING) -> ApprovalResponse:
    return ApprovalResponse(
        id="a1",
        run_id="r1",
        step_position=1,
        tool_name="github.create_issue",
        tool_arguments={"title": "Timeouts"},
        requested_by="oscar",
        status=status,
        decided_by=None if status is ApprovalStatus.PENDING else "ada",
        decision_reason=None,
        created_at=NOW,
        decided_at=None,
    )


class _FakeApprovalService:
    """Mirrors the real rule: only admins decide."""

    async def list_pending(self) -> list[ApprovalResponse]:
        return [_approval()]

    async def decide(
        self, approval_id: str, request: ApprovalDecisionRequest, caller: Caller
    ) -> ApprovalResponse:
        if caller.role is not Role.ADMIN:
            raise PermissionDeniedError("Only admins can approve or reject tool calls")
        return _approval(ApprovalStatus.APPROVED if request.approved else ApprovalStatus.REJECTED)


def _client(key: str) -> AsyncClient:
    overrides = {get_approval_service: lambda: _FakeApprovalService()}
    return build_client([approval_router.router], overrides, key)


async def test_get_approvals_when_pending_lists_them() -> None:
    async with _client("viewer-key") as client:
        response = await client.get("/api/v1/approvals")

    assert response.status_code == 200
    assert [a["tool_name"] for a in response.json()] == ["github.create_issue"]


async def test_post_decision_when_viewer_returns_403() -> None:
    async with _client("viewer-key") as client:
        response = await client.post("/api/v1/approvals/a1/decisions", json={"approved": True})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_post_decision_when_admin_approves_returns_decided_approval() -> None:
    async with _client("admin-key") as client:
        response = await client.post("/api/v1/approvals/a1/decisions", json={"approved": True})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
