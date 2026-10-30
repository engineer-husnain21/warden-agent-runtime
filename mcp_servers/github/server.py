"""GitHub MCP server. Run: `uv run python -m mcp_servers.github.server` (stdio)."""

from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_servers.github.dry_run_github_api import DryRunGitHubApi
from mcp_servers.github.github_api import GitHubApi, IssueState
from mcp_servers.github.github_settings import GitHubSettings
from mcp_servers.github.live_github_api import LiveGitHubApi

MAX_TITLE_LENGTH = 256
MAX_LIST_LIMIT = 100


def create_server(api: GitHubApi, repo: str) -> MCPServer:
    server = MCPServer("github", instructions=f"Issues on the GitHub repository {repo}.")

    @server.tool()
    async def list_issues(state: IssueState = "open", limit: int = 20) -> dict[str, Any]:
        """List issues on the repository, newest first."""
        issues = await api.list_issues(state, max(1, min(limit, MAX_LIST_LIMIT)))
        return {"repo": repo, "issues": issues}

    @server.tool()
    async def create_issue(
        title: str, body: str = "", labels: list[str] | None = None
    ) -> dict[str, Any]:
        """Open a new issue on the repository. This is a real write: it needs approval."""
        clean_title = title.strip()
        if not clean_title or len(clean_title) > MAX_TITLE_LENGTH:
            raise ToolError(f"Title must be 1-{MAX_TITLE_LENGTH} characters")
        issue = await api.create_issue(clean_title, body, labels or [])
        return {"repo": repo, "issue": issue}

    return server


def build_api(settings: GitHubSettings) -> GitHubApi:
    """Dry-run unless GITHUB_MODE=live; live mode refuses to start without a token."""
    if settings.mode == "dry-run":
        return DryRunGitHubApi(settings.repo)
    token = settings.token.get_secret_value() if settings.token else ""
    if not token:
        raise ValueError("GITHUB_TOKEN is required when GITHUB_MODE=live")
    return LiveGitHubApi(settings.repo, token, settings.api_url, httpx.AsyncClient(timeout=30.0))


def main() -> None:
    settings = GitHubSettings()
    create_server(build_api(settings), settings.repo).run("stdio")


if __name__ == "__main__":
    main()
