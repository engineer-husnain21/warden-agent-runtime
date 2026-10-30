from typing import Any

from mcp_servers.github.github_api import IssueState

_FIRST_FAKE_NUMBER = 1000


class DryRunGitHubApi:
    """GitHubApi that never calls GitHub: issues live in memory for the life of the process."""

    def __init__(self, repo: str) -> None:
        self._repo = repo
        self._issues: list[dict[str, Any]] = []

    async def list_issues(self, state: IssueState, limit: int) -> list[dict[str, Any]]:
        matching = [i for i in self._issues if state == "all" or i["state"] == state]
        return list(reversed(matching))[:limit]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        number = _FIRST_FAKE_NUMBER + len(self._issues)
        issue = {
            "number": number,
            "title": title,
            "body": body,
            "state": "open",
            "url": f"https://github.com/{self._repo}/issues/{number}",
            "labels": list(labels),
            "dry_run": True,
        }
        self._issues.append(issue)
        return issue
