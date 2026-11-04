from app.agents.tool_catalog_agent import ToolCatalogAgent
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.tool_catalog_input import ToolCatalogInput
from app.schemas.tool_spec import ToolSpec
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient

TOOLS = [
    ToolSpec(name="warehouse.run_query", server="warehouse", description="SQL", input_schema={}),
    ToolSpec(name="github.create_issue", server="github", description="Issue", input_schema={}),
]


async def test_run_when_called_returns_tools_without_using_llm(
    prompt_loader: FilePromptLoader,
) -> None:
    llm = FakeLlmClient([])

    output = await ToolCatalogAgent(llm, prompt_loader, FakeToolClient(tools=TOOLS)).run(
        ToolCatalogInput()
    )

    assert output.tools == TOOLS
    assert output.usage == []
    assert llm.calls == []
