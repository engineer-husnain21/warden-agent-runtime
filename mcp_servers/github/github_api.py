from typing import Any, Literal, Protocol

IssueState = Literal["open", "closed", "all"]


class GitHubApi(Protocol):
    """Issue operations on one repository. Issues are plain dicts:
    `{"number", "title", "state", "url", "labels"}`. Simulated issues add `"dry_run": True`
    and a `"note"`, and have `"url": None` because they do not exist on GitHub."""

    async def list_issues(self, state: IssueState, limit: int) -> list[dict[str, Any]]: ...

    async def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]: ...
