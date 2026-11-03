import json
from pathlib import Path

import pytest

from evals.eval_summary import EvalSummary
from evals.report_writer import gate_passes, write_reports
from evals.scenario_result import ScenarioResult


def _result(scenario_id: str, passed: bool, failures: list[str]) -> ScenarioResult:
    return ScenarioResult(
        scenario_id=scenario_id,
        passed=passed,
        tool_accuracy=1.0 if passed else 0.5,
        status="completed",
        failures=failures,
        input_tokens=3000,
        output_tokens=125,
        llm_latency_ms=4100.0,
        cost_usd=0.0007,
    )


RESULTS = [_result("a", True, []), _result("b", False, ["report does not mention '35'"])]


@pytest.mark.parametrize(
    ("success", "accuracy", "expected"),
    [(0.8, 0.8, True), (0.79, 1.0, False), (1.0, 0.7, False)],
)
def test_gate_passes_when_scores_compared_needs_both_at_threshold(
    success: float, accuracy: float, expected: bool
) -> None:
    summary = EvalSummary.from_results(RESULTS).model_copy(
        update={"success_rate": success, "tool_accuracy": accuracy}
    )

    assert gate_passes(summary, 0.8) is expected


def test_gate_passes_when_no_scenarios_ran_fails() -> None:
    assert not gate_passes(EvalSummary.from_results([]), 0.8)


def test_write_reports_when_called_writes_json_and_markdown(tmp_path: Path) -> None:
    summary = EvalSummary.from_results(RESULTS)

    json_path, markdown_path = write_reports(RESULTS, summary, tmp_path, 0.8, "groq:model")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["gate_passed"] is False
    assert payload["summary"]["success_rate"] == 0.5
    assert [result["scenario_id"] for result in payload["results"]] == ["a", "b"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "gate **FAILED**" in markdown
    assert "| Task success rate | 0.50 (1/2) |" in markdown
    row = "| b | **fail** | 0.50 | 3,125 | 4.1 | $0.00070 | 1 | report does not mention '35' |"
    assert row in markdown
    assert len(list(tmp_path.glob("eval-*.json"))) == 1
