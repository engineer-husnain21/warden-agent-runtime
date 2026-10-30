import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from mcp_servers.github.dry_run_github_api import DryRunGitHubApi
from mcp_servers.github.server import create_server

REPO = "octo/warden-sandbox"


@pytest.fixture
def server() -> MCPServer:
    return create_server(DryRunGitHubApi(REPO), REPO)


async def test_create_issue_when_dry_run_returns_fake_issue(server: MCPServer) -> None:
    async with Client(server) as client:
        result = await client.call_tool(
            "create_issue", {"title": "Payment timeouts", "body": "Top cause", "labels": ["bug"]}
        )

    assert not result.is_error
    assert result.structured_content is not None
    issue = result.structured_content["issue"]
    assert issue["dry_run"] is True
    assert issue["title"] == "Payment timeouts"
    assert issue["url"] == f"https://github.com/{REPO}/issues/1000"


async def test_list_issues_when_issues_created_returns_newest_first(server: MCPServer) -> None:
    async with Client(server) as client:
        await client.call_tool("create_issue", {"title": "First"})
        await client.call_tool("create_issue", {"title": "Second"})
        result = await client.call_tool("list_issues", {"state": "open"})

    assert result.structured_content is not None
    titles = [issue["title"] for issue in result.structured_content["issues"]]
    assert titles == ["Second", "First"]


async def test_create_issue_when_title_blank_returns_error(server: MCPServer) -> None:
    async with Client(server) as client:
        result = await client.call_tool("create_issue", {"title": "   "})

    assert result.is_error
