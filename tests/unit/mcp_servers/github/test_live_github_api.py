import json
from collections.abc import Callable

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import SecretStr

from mcp_servers.github.dry_run_github_api import DryRunGitHubApi
from mcp_servers.github.github_settings import GitHubSettings
from mcp_servers.github.live_github_api import LiveGitHubApi
from mcp_servers.github.server import build_api

REPO = "octo/warden-sandbox"
ISSUE = {
    "number": 7,
    "title": "Payment timeouts",
    "state": "open",
    "html_url": f"https://github.com/{REPO}/issues/7",
    "labels": [{"name": "bug"}],
}


def _api(handler: Callable[[httpx.Request], httpx.Response]) -> LiveGitHubApi:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LiveGitHubApi(REPO, "test-token", "https://api.github.test", client)


async def test_create_issue_when_live_posts_to_repo() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json=ISSUE)

    issue = await _api(handler).create_issue("Payment timeouts", "Top cause", ["bug"])

    assert issue == {
        "number": 7,
        "title": "Payment timeouts",
        "state": "open",
        "url": f"https://github.com/{REPO}/issues/7",
        "labels": ["bug"],
    }
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == f"https://api.github.test/repos/{REPO}/issues"
    assert request.headers["Authorization"] == "Bearer test-token"
    assert json.loads(request.content) == {
        "title": "Payment timeouts",
        "body": "Top cause",
        "labels": ["bug"],
    }


async def test_list_issues_when_response_has_pull_requests_skips_them() -> None:
    pull_request = {**ISSUE, "number": 8, "pull_request": {"url": "..."}}
    api = _api(lambda _request: httpx.Response(200, json=[ISSUE, pull_request]))

    issues = await api.list_issues("open", 20)

    assert [issue["number"] for issue in issues] == [7]


async def test_create_issue_when_unauthorized_raises_tool_error_without_token() -> None:
    api = _api(lambda _request: httpx.Response(401, json={"message": "Bad credentials"}))

    with pytest.raises(ToolError, match="401: Bad credentials") as caught:
        await api.create_issue("t", "", [])

    assert "test-token" not in str(caught.value)


def test_build_api_when_dry_run_returns_dry_run_api() -> None:
    settings = GitHubSettings(_env_file=None, mode="dry-run", repo=REPO)  # type: ignore[call-arg]

    assert isinstance(build_api(settings), DryRunGitHubApi)


def test_build_api_when_live_without_token_refuses_to_start() -> None:
    settings = GitHubSettings(_env_file=None, mode="live", repo=REPO, token=None)  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        build_api(settings)


def test_build_api_when_live_with_token_returns_live_api() -> None:
    settings = GitHubSettings(  # type: ignore[call-arg]
        _env_file=None, mode="live", repo=REPO, token=SecretStr("t")
    )

    assert isinstance(build_api(settings), LiveGitHubApi)
