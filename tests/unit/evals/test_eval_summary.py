import pytest

from evals.eval_summary import EvalSummary
from evals.scenario_result import ScenarioResult


def _result(passed: bool, accuracy: float, tokens: int, cost: float) -> ScenarioResult:
    return ScenarioResult(
        scenario_id="s",
        passed=passed,
        tool_accuracy=accuracy,
        status="completed",
        input_tokens=tokens,
        llm_latency_ms=3000.0,
        cost_usd=cost,
    )


def test_from_results_when_mixed_computes_rates_and_averages() -> None:
    results = [_result(True, 1.0, 4000, 0.001), _result(False, 0.5, 2000, 0.0005)]

    summary = EvalSummary.from_results(results)

    assert (summary.scenarios, summary.passed, summary.success_rate) == (2, 1, 0.5)
    assert summary.tool_accuracy == 0.75
    assert summary.avg_tokens_per_run == 3000
    assert summary.avg_llm_latency_seconds == 3.0
    assert summary.total_cost_usd == pytest.approx(0.0015)


def test_from_results_when_empty_scores_zero() -> None:
    summary = EvalSummary.from_results([])

    assert (summary.scenarios, summary.success_rate) == (0, 0.0)
