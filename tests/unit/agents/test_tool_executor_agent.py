from app.agents.tool_executor_agent import ToolExecutorAgent
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.tool_executor_input import ToolExecutorInput
from app.schemas.tool_call import ToolCall
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient


async def test_run_when_called_never_uses_llm_client(prompt_loader: FilePromptLoader) -> None:
    llm = FakeLlmClient([])
    tools = FakeToolClient(results={"warehouse.run_query": {"rows": [{"n": 3}]}})
    call = ToolCall(tool="warehouse.run_query", arguments={"sql": "SELECT 3 AS n"})

    output = await ToolExecutorAgent(llm, prompt_loader, tools).run(ToolExecutorInput(call=call))

    assert output.result.ok
    assert output.result.content == {"rows": [{"n": 3}]}
    assert output.usage == []
    assert llm.calls == []
    assert tools.calls == [call]


async def test_run_when_tool_fails_returns_failed_result(prompt_loader: FilePromptLoader) -> None:
    tools = FakeToolClient(errors={"github.create_issue": "GitHub API error 401"})

    output = await ToolExecutorAgent(FakeLlmClient([]), prompt_loader, tools).run(
        ToolExecutorInput(call=ToolCall(tool="github.create_issue", arguments={"title": "t"}))
    )

    assert not output.result.ok
    assert output.result.error == "GitHub API error 401"
