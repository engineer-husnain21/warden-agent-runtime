import json

import pytest

from app.agents.tool_selector_agent import ToolSelectorAgent
from app.core.exceptions import AgentOutputError
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.plan_step import PlanStep
from app.schemas.agents.tool_selector_input import ToolSelectorInput
from app.schemas.tool_spec import ToolSpec
from tests.fakes.fake_llm_client import FakeLlmClient


def _input(tools: list[ToolSpec], feedback: str | None = None) -> ToolSelectorInput:
    return ToolSelectorInput(
        task="Open an issue for the top failure cause",
        step=PlanStep(description="Count failed orders by failure_reason"),
        tools=tools,
        previous_results=["warehouse.list_tables -> orders"],
        feedback=feedback,
    )


async def test_run_when_llm_picks_known_tool_returns_call(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    reply = {
        "tool": "warehouse.run_query",
        "arguments": {"sql": "SELECT failure_reason, COUNT(*) FROM orders GROUP BY 1"},
        "reasoning": "Aggregate failures by reason.",
    }
    llm = FakeLlmClient([json.dumps(reply)])

    output = await ToolSelectorAgent(llm, prompt_loader).run(
        _input(tool_specs, feedback="Use GROUP BY")
    )

    assert output.tool == "warehouse.run_query"
    assert output.arguments["sql"].startswith("SELECT")
    assert len(output.usage) == 1
    user_message = llm.calls[0][1].content
    assert "Count failed orders by failure_reason" in user_message
    assert "- warehouse.list_tables -> orders" in user_message
    assert "Use GROUP BY" in user_message
    assert '"sql"' in user_message


async def test_run_when_tool_unknown_raises_agent_output_error(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    bad = json.dumps({"tool": "shell.run", "arguments": {"cmd": "ls"}})
    llm = FakeLlmClient([bad, bad])

    with pytest.raises(AgentOutputError, match="unknown tool"):
        await ToolSelectorAgent(llm, prompt_loader).run(_input(tool_specs))


async def test_run_when_unknown_tool_then_fixed_returns_repaired_call(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    llm = FakeLlmClient(
        [
            json.dumps({"tool": "warehouse.query", "arguments": {"sql": "SELECT 1"}}),
            json.dumps({"tool": "warehouse.run_query", "arguments": {"sql": "SELECT 1"}}),
        ]
    )

    output = await ToolSelectorAgent(llm, prompt_loader).run(_input(tool_specs))

    assert output.tool == "warehouse.run_query"
    assert len(output.usage) == 2
    assert "unknown tool: warehouse.query" in llm.calls[1][-1].content


async def test_run_when_required_argument_missing_raises_agent_output_error(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    tools = [
        spec.model_copy(update={"input_schema": {**spec.input_schema, "required": ["sql"]}})
        for spec in tool_specs
    ]
    bad = json.dumps({"tool": "warehouse.run_query", "arguments": {}})
    llm = FakeLlmClient([bad, bad])

    with pytest.raises(AgentOutputError, match="sql"):
        await ToolSelectorAgent(llm, prompt_loader).run(_input(tools))
