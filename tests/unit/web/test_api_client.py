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
