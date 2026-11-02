import re

from app.agents.base_agent import BaseAgent
from app.agents.tool_result_text import format_tool_result
from app.core.exceptions import AgentOutputError
from app.schemas.agents.reporter_input import ReporterInput
from app.schemas.agents.reporter_output import ReporterOutput
from app.schemas.agents.step_record import StepRecord

DRY_RUN_LABEL = "(dry-run, not created)"
_MARKDOWN_ISSUE_LINK = re.compile(r"\[([^\]]*)\]\(https?://github\.com/[^)\s]+/issues/(\d+)\)")
_BARE_ISSUE_URL = re.compile(r"<?https?://github\.com/[^\s)>]+/issues/(\d+)>?")


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
        report = _unlink_dry_run_issues(report, _dry_run_issue_numbers(input.steps))
        return ReporterOutput(report=report, usage=[usage])


def _dry_run_issue_numbers(steps: list[StepRecord]) -> set[str]:
    numbers: set[str] = set()
    for step in steps:
        content = step.result.content if step.result is not None else None
        issue = (content or {}).get("issue")
        if isinstance(issue, dict) and issue.get("dry_run") and issue.get("number") is not None:
            numbers.add(str(issue["number"]))
    return numbers


def _unlink_dry_run_issues(report: str, numbers: set[str]) -> str:
    """A dry-run issue does not exist, so a link to it would 404. The prompt asks the model not
    to link it; this makes sure, even if the model builds a URL anyway."""
    if not numbers:
        return report

    def replace_markdown_link(match: re.Match[str]) -> str:
        text, number = match.group(1), match.group(2)
        return f"{text} {DRY_RUN_LABEL}" if number in numbers else match.group(0)

    def replace_bare_url(match: re.Match[str]) -> str:
        return DRY_RUN_LABEL if match.group(1) in numbers else match.group(0)

    report = _MARKDOWN_ISSUE_LINK.sub(replace_markdown_link, report)
    return _BARE_ISSUE_URL.sub(replace_bare_url, report)


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
