from app.agents.base_agent import BaseAgent
from app.clients.llm_client import LlmClient
from app.clients.tool_client import ToolClient
from app.core.prompt_loader import PromptLoader
from app.schemas.agents.tool_executor_input import ToolExecutorInput
from app.schemas.agents.tool_executor_output import ToolExecutorOutput


class ToolExecutorAgent(BaseAgent[ToolExecutorInput, ToolExecutorOutput]):
    """Runs one already-approved tool call through the ToolClient. Uses no LLM.

    It keeps the BaseAgent constructor contract (llm_client, prompt_loader) so every agent is
    built and injected the same way, and adds the ToolClient. See docs/adr/0001.
    """

    name = "tool_executor"

    def __init__(
        self, llm_client: LlmClient, prompt_loader: PromptLoader, tool_client: ToolClient
    ) -> None:
        super().__init__(llm_client, prompt_loader)
        self._tool_client = tool_client

    async def run(self, input: ToolExecutorInput) -> ToolExecutorOutput:
        result = await self._tool_client.call_tool(input.call)
        return ToolExecutorOutput(result=result)
