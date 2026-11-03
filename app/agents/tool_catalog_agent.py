from app.agents.base_agent import BaseAgent
from app.clients.llm_client import LlmClient
from app.clients.tool_client import ToolClient
from app.core.prompt_loader import PromptLoader
from app.schemas.agents.tool_catalog_input import ToolCatalogInput
from app.schemas.agents.tool_catalog_output import ToolCatalogOutput


class ToolCatalogAgent(BaseAgent[ToolCatalogInput, ToolCatalogOutput]):
    """Lists the MCP tools a run can use, through the ToolClient. Uses no LLM.

    Like ToolExecutorAgent (docs/adr/0001), it keeps the BaseAgent constructor contract and adds
    the ToolClient, so the orchestrator reaches tools only through agents.
    """

    name = "tool_catalog"

    def __init__(
        self, llm_client: LlmClient, prompt_loader: PromptLoader, tool_client: ToolClient
    ) -> None:
        super().__init__(llm_client, prompt_loader)
        self._tool_client = tool_client

    async def run(self, input: ToolCatalogInput) -> ToolCatalogOutput:
        return ToolCatalogOutput(tools=await self._tool_client.list_tools())
