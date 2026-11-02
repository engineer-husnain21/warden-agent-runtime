from app.agents.base_agent import BaseAgent
from app.agents.tool_result_text import format_tool_result
from app.core.exceptions import AgentOutputError
from app.schemas.agents.reporter_input import ReporterInput
from app.schemas.agents.reporter_output import ReporterOutput
from app.schemas.agents.step_record import StepRecord


class ReporterAgent(BaseAgent[ReporterInput, ReporterOutput]):
    """Writes the final Markdown report of a run from its step records."""

    name = "reporter"

    async def run(self, input: ReporterInput) -> ReporterOutput:
        not_done = sum(1 for step in input.steps if step.outcome != "succeeded")
        messages = await self._build_messages(
            "reporter",
            task=input.task,
            steps=_format_steps(input.steps),
            not_done_count=str(not_done),
        )
        report, usage = await self._complete_text(messages)
        if not report:
            raise AgentOutputError(
                f"{self.name} returned an empty report", details={"agent": self.name}
            )
        return ReporterOutput(report=report, usage=[usage])


def _format_steps(steps: list[StepRecord]) -> str:
    if not steps:
        return "(no steps were run)"
    lines = []
    for number, step in enumerate(steps, start=1):
        lines.append(f"{number}. {step.description} [{step.outcome}]")
        if step.tool:
            lines.append(f"   tool: {step.tool}")
        if step.result is not None:
            lines.append(f"   result: {format_tool_result(step.result)}")
        if step.note:
            lines.append(f"   note: {step.note}")
    return "\n".join(lines)
