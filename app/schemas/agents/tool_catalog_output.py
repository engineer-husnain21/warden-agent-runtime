from app.schemas.agents.base_agent_output import BaseAgentOutput
from app.schemas.tool_spec import ToolSpec


class ToolCatalogOutput(BaseAgentOutput):
    """The tools the run can plan with. `usage` stays empty: listing tools uses no LLM."""

    tools: list[ToolSpec]
