from pathlib import Path

import pytest
from pydantic import BaseModel

from app.agents.base_agent import BaseAgent
from app.core.exceptions import AgentOutputError
from app.core.file_prompt_loader import FilePromptLoader
from tests.fakes.fake_llm_client import FakeLlmClient


class _EchoInput(BaseModel):
    text: str


class _EchoOutput(BaseModel):
    echo: str


class _EchoAgent(BaseAgent[_EchoInput, _EchoOutput]):
    name = "echo"

    async def run(self, input: _EchoInput) -> _EchoOutput:
        messages = await self._build_messages("echo", text=input.text)
        reply, _ = await self._complete_json(messages, _EchoOutput)
        return reply


def _agent(tmp_path: Path, replies: list[str]) -> tuple[_EchoAgent, FakeLlmClient]:
    (tmp_path / "echo_system.md").write_text("Reply with JSON.", encoding="utf-8")
    (tmp_path / "echo_user.md").write_text("Echo: $text", encoding="utf-8")
    (tmp_path / "json_repair_user.md").write_text("Fix: $error", encoding="utf-8")
    llm = FakeLlmClient(replies)
    return _EchoAgent(llm, FilePromptLoader(tmp_path)), llm


def test_base_agent_when_run_not_implemented_cannot_instantiate(tmp_path: Path) -> None:
    class _Incomplete(BaseAgent[_EchoInput, _EchoOutput]):
        name = "incomplete"

    with pytest.raises(TypeError):
        _Incomplete(FakeLlmClient([]), FilePromptLoader(tmp_path))  # type: ignore[abstract]


async def test_run_when_reply_valid_fills_prompts_and_parses(tmp_path: Path) -> None:
    agent, llm = _agent(tmp_path, ['{"echo": "hi"}'])

    output = await agent.run(_EchoInput(text="hi"))

    assert output == _EchoOutput(echo="hi")
    assert [m.content for m in llm.calls[0]] == ["Reply with JSON.", "Echo: hi"]


async def test_run_when_reply_in_code_fence_still_parses(tmp_path: Path) -> None:
    agent, _ = _agent(tmp_path, ['```json\n{"echo": "fenced"}\n```'])

    assert (await agent.run(_EchoInput(text="x"))).echo == "fenced"


async def test_run_when_json_invalid_twice_raises_agent_output_error(tmp_path: Path) -> None:
    agent, llm = _agent(tmp_path, ["Sure! Here you go.", '{"wrong": 1}'])

    with pytest.raises(AgentOutputError):
        await agent.run(_EchoInput(text="x"))

    assert len(llm.calls) == 2


async def test_run_when_first_reply_invalid_repairs_once(tmp_path: Path) -> None:
    agent, llm = _agent(tmp_path, ["not json", '{"echo": "fixed"}'])

    output = await agent.run(_EchoInput(text="x"))

    assert output.echo == "fixed"
    repair_turn = llm.calls[1]
    assert [m.role for m in repair_turn] == ["system", "user", "assistant", "user"]
    assert repair_turn[2].content == "not json"
    assert repair_turn[3].content.startswith("Fix: echo returned output")
