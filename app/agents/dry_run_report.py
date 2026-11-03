"""Deterministic clean-up of how simulated (dry-run) GitHub issues appear in the final report.

A dry-run issue was never created, so the report must not link to it or quote its fake number.
The prompt asks for this; these helpers make sure of it. Whatever the model wrote about a
dry-run issue under "Actions taken" is replaced by one fixed line per issue.
"""

import re
from typing import Any

from app.schemas.agents.step_record import StepRecord

DRY_RUN_LABEL = "(dry-run, nothing was created)"
# Models like the non-breaking hyphen (U+2011); the report uses plain ASCII hyphens.
_UNICODE_HYPHENS = str.maketrans({"\u2010": "-", "\u2011": "-"})
_MARKDOWN_ISSUE_LINK = re.compile(r"\[([^\]]*)\]\(https?://github\.com/[^)\s]+/issues/(\d+)\)")
_BARE_ISSUE_URL = re.compile(r"<?https?://github\.com/[^\s)>]+/issues/(\d+)>?")
_HEADING = re.compile(r"^#{1,6}\s")
_ACTIONS_HEADING = re.compile(r"^#{1,6}\s*actions taken\b", re.IGNORECASE)
_NOT_DONE_HEADING = re.compile(r"^#{1,6}\s*not done\b", re.IGNORECASE)
_BULLET = re.compile(r"^ ?(?:[-*+]|\d+[.)])\s")


def dry_run_action_line(title: str) -> str:
    return f"- Would create GitHub issue {DRY_RUN_LABEL}: {title}"


def dry_run_issues(steps: list[StepRecord]) -> list[dict[str, Any]]:
    """The simulated issues among the step results, in step order."""
    issues: list[dict[str, Any]] = []
    for step in steps:
        content = step.result.content if step.result is not None else None
        issue = (content or {}).get("issue")
        if isinstance(issue, dict) and issue.get("dry_run"):
            issues.append(issue)
    return issues


def clean_dry_run_report(report: str, issues: list[dict[str, Any]]) -> str:
    report = report.translate(_UNICODE_HYPHENS)
    if not issues:
        return report
    numbers = {str(issue["number"]) for issue in issues if issue.get("number") is not None}
    return _rewrite_actions(_unlink(report, numbers), issues)


def _unlink(report: str, numbers: set[str]) -> str:
    """A link to an issue that was never created would 404, even if the model builds one."""

    def replace_markdown_link(match: re.Match[str]) -> str:
        text, number = match.group(1), match.group(2)
        return f"{text} {DRY_RUN_LABEL}" if number in numbers else match.group(0)

    def replace_bare_url(match: re.Match[str]) -> str:
        return DRY_RUN_LABEL if match.group(1) in numbers else match.group(0)

    report = _MARKDOWN_ISSUE_LINK.sub(replace_markdown_link, report)
    return _BARE_ISSUE_URL.sub(replace_bare_url, report)


def _rewrite_actions(report: str, issues: list[dict[str, Any]]) -> str:
    lines = report.split("\n")
    fixed = [dry_run_action_line(issue.get("title") or "untitled issue") for issue in issues]
    start = next((i for i, line in enumerate(lines) if _ACTIONS_HEADING.match(line)), None)
    if start is None:  # the model left the section out: add it before "Not done" or at the end
        at = next((i for i, line in enumerate(lines) if _NOT_DONE_HEADING.match(line)), None)
        if at is None:
            return "\n".join([*lines, "", "## Actions taken", *fixed])
        return "\n".join([*lines[:at], "## Actions taken", *fixed, "", *lines[at:]])
    end = next((i for i in range(start + 1, len(lines)) if _HEADING.match(lines[i])), len(lines))
    kept = [
        line
        for block in _blocks(lines[start + 1 : end])
        if not _describes_dry_run(block, issues)
        for line in block
    ]
    body = [*fixed, *"\n".join(kept).strip("\n").split("\n")] if any(kept) else fixed
    tail = ["", *lines[end:]] if end < len(lines) else []
    return "\n".join([*lines[: start + 1], *body, *tail])


def _blocks(lines: list[str]) -> list[list[str]]:
    """Split a section into list items (with their indented continuation lines) and plain lines."""
    blocks: list[list[str]] = []
    for line in lines:
        starts_block = _BULLET.match(line) or (line.strip() and not line[0].isspace())
        if starts_block or not blocks:
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return blocks


def _describes_dry_run(block: list[str], issues: list[dict[str, Any]]) -> bool:
    text = "\n".join(block).lower()
    if text.strip().rstrip(".") == "none":
        return True  # "None" no longer holds: there is a dry-run action
    if "dry-run" in text or "dry_run" in text:
        return True
    for issue in issues:
        title = (issue.get("title") or "").lower()
        if title and title in text:
            return True
        if issue.get("number") is not None and re.search(rf"#{issue['number']}\b", text):
            return True
    return False
