from app.schemas.agents.base_agent_output import BaseAgentOutput
from app.schemas.tool_result import ToolResult


class ToolExecutorOutput(BaseAgentOutput):
    """The raw tool result. `usage` stays empty: executing a tool uses no LLM."""

    result: ToolResult
