from app.agents.base_agent import BaseAgent
from app.schemas.agents.planner_input import PlannerInput
from app.schemas.agents.planner_output import PlannerOutput
from app.schemas.tool_spec import ToolSpec


class PlannerAgent(BaseAgent[PlannerInput, PlannerOutput]):
    """Splits a task into ordered steps, one tool call each."""

    name = "planner"

    async def run(self, input: PlannerInput) -> PlannerOutput:
        messages = await self._build_messages(
            "planner", task=input.task, tools=format_tool_list(input.tools)
        )
        plan, usage = await self._complete_json(messages, PlannerOutput)
        return plan.model_copy(update={"usage": usage})


def format_tool_list(tools: list[ToolSpec]) -> str:
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools) or "(none)"
