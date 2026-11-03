import json

import httpx
import pytest

from web.api_client import WardenApiClient
from web.warden_api_error import WardenApiError


def test_api_client_when_create_run_posts_task() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(202, json={"id": "r1", "status": "pending"})

    client = WardenApiClient(
        "http://api.test/", "operator-key", transport=httpx.MockTransport(handler)
    )

    run = client.create_run("Find failed orders")

    assert run == {"id": "r1", "status": "pending"}
    request = seen[0]
    assert str(request.url) == "http://api.test/api/v1/agent-runs"
    assert request.headers["X-API-Key"] == "operator-key"
    assert json.loads(request.content) == {"task": "Find failed orders"}


def test_api_client_when_api_returns_error_raises_with_its_message() -> None:
    body = {"error": {"code": "permission_denied", "message": "Only admins can approve"}}
    transport = httpx.MockTransport(lambda _request: httpx.Response(403, json=body))
    client = WardenApiClient("http://api.test", "viewer-key", transport=transport)

    with pytest.raises(WardenApiError) as caught:
        client.decide("a1", approved=True, reason=None)

    assert (caught.value.status_code, caught.value.message) == (403, "Only admins can approve")


def test_api_client_when_api_down_raises_not_reachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = WardenApiClient("http://api.test", "k", transport=httpx.MockTransport(handler))

    with pytest.raises(WardenApiError, match="not reachable"):
        client.list_runs()


@pytest.mark.parametrize(
    "pasted_key", [" operator-dev-key", "operator-dev-key\n", "\toperator-dev-key  "]
)
def test_api_client_when_key_has_whitespace_sends_stripped_key(pasted_key: str) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    client = WardenApiClient(
        " http://api.test/ ", pasted_key, transport=httpx.MockTransport(handler)
    )

    client.list_runs()

    assert seen[0].headers["X-API-Key"] == "operator-dev-key"
    assert str(seen[0].url).startswith("http://api.test/api/v1/agent-runs")


def test_api_client_when_approvals_listed_with_context_adds_task_role_and_reason() -> None:
    calls: list[str] = []
    approvals = [
        {"id": "a1", "run_id": "r1", "tool_name": "github.create_issue"},
        {"id": "a2", "run_id": "r1", "tool_name": "notifier.send_notification"},
    ]
    run = {"id": "r1", "task": "Find failed orders", "role": "operator"}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200, json=approvals if request.url.path.endswith("/approvals") else run
        )

    client = WardenApiClient("http://api.test", "k", transport=httpx.MockTransport(handler))

    enriched = client.list_pending_approvals_with_context()

    assert [a["run_task"] for a in enriched] == ["Find failed orders", "Find failed orders"]
    assert enriched[0]["requested_role"] == "operator"
    assert "'operator' role may call github.create_issue" in enriched[0]["policy_reason"]
    assert calls == ["/api/v1/approvals", "/api/v1/agent-runs/r1"]  # run fetched once


def test_api_client_when_overview_requested_counts_runs_and_sums_cost() -> None:
    runs = [
        {"id": "r1", "status": "completed"},
        {"id": "r2", "status": "awaiting_approval"},
        {"id": "r3", "status": "failed"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metrics"):
            return httpx.Response(200, json={"total_cost_usd": 0.001})
        return httpx.Response(200, json=runs)

    client = WardenApiClient("http://api.test", "k", transport=httpx.MockTransport(handler))

    overview = client.get_overview()

    assert (overview["total_runs"], overview["awaiting_approval"], overview["completed"]) == (
        3,
        1,
        1,
    )
    assert overview["total_cost_usd"] == pytest.approx(0.003)
    assert overview["active"] is True
    assert overview["status_counts"] == {"completed": 1, "awaiting_approval": 1, "failed": 1}


def test_api_client_when_all_runs_finished_overview_is_not_active() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metrics"):
            return httpx.Response(200, json={"total_cost_usd": 0.0})
        return httpx.Response(200, json=[{"id": "r1", "status": "completed"}])

    client = WardenApiClient("http://api.test", "k", transport=httpx.MockTransport(handler))

    assert client.get_overview()["active"] is False
