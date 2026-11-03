from typing import Any

from app.agents.dry_run_report import clean_dry_run_report, dry_run_issues
from app.schemas.agents.step_record import StepRecord
from app.schemas.tool_result import ToolResult

ISSUE: dict[str, Any] = {
    "number": 1000,
    "title": "Top 3 Order Failure Causes (Last 24h)",
    "url": None,
    "dry_run": True,
}
LINE = (
    "- Would create GitHub issue (dry-run, nothing was created): "
    "Top 3 Order Failure Causes (Last 24h)"
)

# What gpt-oss-120b actually wrote on a dry-run demo run (non-breaking hyphens, fake number).
MODEL_REPLY = """## Summary
Found the top 3 causes and opened an issue (dry\u2011run).

## Actions taken
- GitHub issue created (dry\u2011run, not created) in **octo/warden-sandbox**:
  **#1000 \u2013 Top 3 Order Failure Causes (Last 24h)**
  Body:
  ```
  - payment_timeout: 14
  ```
- Notification sent to #ops

## Not done
Nothing else."""


def test_clean_dry_run_report_when_model_wording_given_replaces_it_with_fixed_line() -> None:
    report = clean_dry_run_report(MODEL_REPLY, [ISSUE])

    assert report == (
        "## Summary\n"
        "Found the top 3 causes and opened an issue (dry-run).\n\n"
        f"## Actions taken\n{LINE}\n- Notification sent to #ops\n\n"
        "## Not done\nNothing else."
    )
    assert "#1000" not in report
    assert "\u2011" not in report


def test_clean_dry_run_report_when_section_says_none_replaces_none() -> None:
    report = clean_dry_run_report("## Summary\nDone.\n\n## Actions taken\nNone", [ISSUE])

    assert report == f"## Summary\nDone.\n\n## Actions taken\n{LINE}"


def test_clean_dry_run_report_when_section_missing_adds_it() -> None:
    assert clean_dry_run_report("## Summary\nDone.", [ISSUE]) == (
        f"## Summary\nDone.\n\n## Actions taken\n{LINE}"
    )


def test_clean_dry_run_report_when_no_dry_run_issue_only_fixes_hyphens() -> None:
    report = "## Actions taken\n- Created [#7](https://github.com/o/r/issues/7) (non\u2011urgent)"

    assert clean_dry_run_report(report, []) == (
        "## Actions taken\n- Created [#7](https://github.com/o/r/issues/7) (non-urgent)"
    )


def test_dry_run_issues_when_steps_mixed_returns_only_simulated_issues() -> None:
    def step(issue: dict[str, Any]) -> StepRecord:
        result = ToolResult(tool="github.create_issue", ok=True, content={"issue": issue})
        return StepRecord(description="d", outcome="succeeded", tool=result.tool, result=result)

    live = {"number": 7, "title": "Live", "url": "https://github.com/o/r/issues/7"}
    steps = [step(live), step(ISSUE), StepRecord(description="d", outcome="denied")]

    assert dry_run_issues(steps) == [ISSUE]
