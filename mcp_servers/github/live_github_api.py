from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from mcp_servers.github.github_api import IssueState

GITHUB_API_VERSION = "2022-11-28"


class LiveGitHubApi:
    """GitHubApi over the GitHub REST API. The token should be scoped to this one repo."""

    def __init__(self, repo: str, token: str, api_url: str, http_client: httpx.AsyncClient) -> None:
        self._issues_url = f"{api_url.rstrip('/')}/repos/{repo}/issues"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "warden-agent-runtime",
        }
        self._http = http_client

    async def list_issues(self, state: IssueState, limit: int) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {"state": state, "per_page": limit}
        response = await self._http.get(self._issues_url, params=params, headers=self._headers)
        items: list[dict[str, Any]] = _json_or_raise(response)
        # The issues endpoint also returns pull requests; keep real issues only.
        return [_to_issue(item) for item in items if "pull_request" not in item]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        payload = {"title": title, "body": body, "labels": labels}
        response = await self._http.post(self._issues_url, json=payload, headers=self._headers)
        return _to_issue(_json_or_raise(response))


def _json_or_raise(response: httpx.Response) -> Any:
    if response.is_error:
        try:
            message = response.json().get("message", "")
        except ValueError:
            message = ""
        raise ToolError(f"GitHub API error {response.status_code}: {message}".strip())
    return response.json()


def _to_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item["number"],
        "title": item["title"],
        "state": item["state"],
        "url": item["html_url"],
        "labels": [label["name"] for label in item.get("labels", [])],
    }
