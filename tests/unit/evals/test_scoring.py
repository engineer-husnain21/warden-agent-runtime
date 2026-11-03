import pytest

from evals.scoring import score_run, tool_accuracy
from tests.unit.evals.scenario_factory import APPROVED_STEPS, ISSUE, METRICS, make_scenario, step

REPORT = "## Actions taken\n- Would create GitHub issue (dry-run, nothing was created): Timeouts"
COMPLETED = {"id": "r1", "status": "completed", "error": None}


def test_score_when_expected_tools_match_returns_full_accuracy() -> None:
    result = score_run(make_scenario(), COMPLETED, APPROVED_STEPS, REPORT, METRICS)

    assert result.passed
    assert result.failures == []
    assert result.tool_accuracy == 1.0
    assert result.picked_tools == [ISSUE]
    assert (result.input_tokens, result.cost_usd) == (3000, 0.00075)


@pytest.mark.parametrize(
    ("picked", "expected_accuracy"),
    [
        ({"warehouse.run_query", "warehouse.describe_table"}, 1.0),  # schema look-up is allowed
        ({"warehouse.run_query", "notifier.send_notification"}, 0.5),
        ({"github.list_issues"}, 0.0),
        (set(), 0.0),
    ],
)
def test_tool_accuracy_when_tools_differ_scores_overlap(
    picked: set[str], expected_accuracy: float
) -> None:
    allowed = {"warehouse.list_tables", "warehouse.describe_table"}

    assert tool_accuracy({"warehouse.run_query"}, picked, allowed) == expected_accuracy


def test_score_when_run_misbehaves_lists_every_failure() -> None:
    scenario = make_scenario(
        role="viewer",
        approval="none",
        expect={
            "tools": [ISSUE],
            "denied": [ISSUE],
            "not_executed": [ISSUE],
            "report_excludes": ["github.com"],
        },
    )
    failed = {"id": "r2", "status": "failed", "error": "LLM call failed: 429"}

    result = score_run(
        scenario, failed, APPROVED_STEPS, "See github.com/o/r/issues/1", METRICS, ["paused"]
    )

    assert not result.passed
    assert result.failures == [
        "paused",
        "status failed, expected completed (LLM call failed: 429)",
        f"ran {ISSUE}, which must not run",
        f"{ISSUE} was not denied",
        "report mentions 'github.com'",
    ]


def test_score_when_tool_denied_and_not_run_passes() -> None:
    scenario = make_scenario(
        role="viewer",
        approval="none",
        expect={"tools": [ISSUE], "denied": [ISSUE], "not_executed": [ISSUE]},
    )
    steps = [step("tool_selection", tool=ISSUE), step("permission_check", "denied", ISSUE)]

    assert score_run(scenario, COMPLETED, steps, "", METRICS).passed
