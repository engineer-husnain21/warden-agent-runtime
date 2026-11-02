import json

from app.agents.base_agent import BaseAgent
from app.core.exceptions import AgentOutputError
from app.schemas.agents.tool_selector_input import ToolSelectorInput
from app.schemas.agents.tool_selector_output import ToolSelectorOutput
from app.schemas.tool_spec import ToolSpec


class ToolSelectorAgent(BaseAgent[ToolSelectorInput, ToolSelectorOutput]):
    """Picks the tool and arguments for one plan step."""

    name = "tool_selector"

    async def run(self, input: ToolSelectorInput) -> ToolSelectorOutput:
        messages = await self._build_messages(
            "tool_selector",
            task=input.task,
            step=input.step.description,
            previous_results="\n".join(f"- {r}" for r in input.previous_results) or "(none)",
            feedback=input.feedback or "(none)",
            tools=_format_tools_with_schemas(input.tools),
        )
        selection, usage = await self._complete_json(messages, ToolSelectorOutput)
        self._check_selection(selection, input.tools)
        return selection.model_copy(update={"usage": usage})

    def _check_selection(self, selection: ToolSelectorOutput, tools: list[ToolSpec]) -> None:
        spec = next((tool for tool in tools if tool.name == selection.tool), None)
        if spec is None:
            raise AgentOutputError(
                f"{self.name} picked an unknown tool: {selection.tool}",
                details={"agent": self.name, "tool": selection.tool},
            )
        missing = [
            name
            for name in spec.input_schema.get("required", [])
            if name not in selection.arguments
        ]
        if missing:
            raise AgentOutputError(
                f"{self.name} left out required arguments for {spec.name}: {', '.join(missing)}",
                details={"agent": self.name, "tool": spec.name, "missing": missing},
            )


def _format_tools_with_schemas(tools: list[ToolSpec]) -> str:
    return "\n".join(
        f"- {tool.name}: {tool.description}\n  arguments schema: {json.dumps(tool.input_schema)}"
        for tool in tools
    )
