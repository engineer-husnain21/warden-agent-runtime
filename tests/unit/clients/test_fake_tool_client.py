import pytest
from pydantic import ValidationError

from app.clients.tool_client import ToolClient
from app.schemas.tool_call import ToolCall
from tests.fakes.fake_tool_client import FakeToolClient


async def test_fake_tool_client_when_called_returns_scripted_result() -> None:
    client: ToolClient = FakeToolClient(results={"warehouse.run_query": {"rows": [{"n": 1}]}})

    result = await client.call_tool(ToolCall(tool="warehouse.run_query", arguments={"sql": "x"}))

    assert result.ok
    assert result.content == {"rows": [{"n": 1}]}


async def test_fake_tool_client_when_tool_unknown_returns_not_ok() -> None:
    result = await FakeToolClient().call_tool(ToolCall(tool="github.create_issue"))

    assert not result.ok
    assert result.error == "Unknown tool: github.create_issue"


def test_tool_call_when_qualified_name_splits_server_and_tool() -> None:
    call = ToolCall(tool="github.create_issue")

    assert (call.server, call.tool_name) == ("github", "create_issue")


@pytest.mark.parametrize("name", ["create_issue", "github.", "GitHub.create_issue", "a.b.c"])
def test_tool_call_when_name_not_qualified_fails_validation(name: str) -> None:
    with pytest.raises(ValidationError):
        ToolCall(tool=name)
