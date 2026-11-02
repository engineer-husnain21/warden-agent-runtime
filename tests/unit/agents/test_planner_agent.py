import json

import pytest

from app.agents.planner_agent import PlannerAgent
from app.core.exceptions import AgentOutputError
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.agents.planner_input import PlannerInput
from app.schemas.tool_spec import ToolSpec
from tests.fakes.fake_llm_client import FakeLlmClient

TASK = "Find orders that failed in the last 24 hours and open a GitHub issue for the top 3 causes"


async def test_run_when_llm_returns_steps_returns_plan(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    reply = {
        "steps": [
            {"description": "Count failed orders in the last 24h by failure_reason."},
            {"description": "Open one issue listing the top 3 causes."},
        ]
    }
    llm = FakeLlmClient([json.dumps(reply)])

    output = await PlannerAgent(llm, prompt_loader).run(PlannerInput(task=TASK, tools=tool_specs))

    assert [step.description for step in output.steps] == [
        "Count failed orders in the last 24h by failure_reason.",
        "Open one issue listing the top 3 causes.",
    ]
    assert len(output.usage) == 1
    user_message = llm.calls[0][1].content
    assert TASK in user_message
    assert "- warehouse.run_query: Run one read-only SQL SELECT." in user_message


async def test_run_when_task_impossible_returns_empty_plan(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    llm = FakeLlmClient(['{"steps": []}'])

    output = await PlannerAgent(llm, prompt_loader).run(
        PlannerInput(task="Book me a flight", tools=tool_specs)
    )

    assert output.steps == []


async def test_run_when_too_many_steps_raises_agent_output_error(
    prompt_loader: FilePromptLoader, tool_specs: list[ToolSpec]
) -> None:
    reply = {"steps": [{"description": f"step {i}"} for i in range(9)]}
    llm = FakeLlmClient([json.dumps(reply)])

    with pytest.raises(AgentOutputError):
        await PlannerAgent(llm, prompt_loader).run(PlannerInput(task=TASK, tools=tool_specs))
