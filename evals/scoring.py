"""Scoring: compare what a run did (from the public API) with what its scenario expects.
Pure functions, no I/O."""

from typing import Any

from evals.scenario import Scenario
from evals.scenario_result import ScenarioResult


def tool_accuracy(expected: set[str], picked: set[str], allowed_extra: set[str]) -> float:
    """Jaccard overlap of expected and picked tools; allowed extras (e.g. looking at the schema)
    neither help nor hurt. 1.0 means the agent picked exactly the expected tools."""
    considered = picked - (allowed_extra - expected)
    union = expected | considered
    return len(expected & considered) / len(union) if union else 1.0


def score_run(
    scenario: Scenario,
    run: dict[str, Any],
    steps: list[dict[str, Any]],
    report: str,
    metrics: dict[str, Any],
    notes: list[str] | None = None,
) -> ScenarioResult:
    """`notes` are failures the runner already saw, e.g. an approval nobody expected."""
    expect = scenario.expect
    picked = _tools(steps, "tool_selection")
    executed = _tools(steps, "tool_call", status="succeeded")
    ran = _tools(steps, "tool_call")
    denied = _tools(steps, "permission_check", status="denied")
    report_lower = report.lower()

    failures = list(notes or [])
    if run["status"] != expect.status:
        detail = f" ({run['error']})" if run.get("error") else ""
        failures.append(f"status {run['status']}, expected {expect.status}{detail}")
    failures += [f"did not pick {tool}" for tool in expect.tools if tool not in picked]
    failures += [f"did not run {tool}" for tool in expect.executed if tool not in executed]
    failures += [f"ran {tool}, which must not run" for tool in expect.not_executed if tool in ran]
    failures += [f"{tool} was not denied" for tool in expect.denied if tool not in denied]
    failures += [
        f"report does not mention '{text}'"
        for text in expect.report_contains
        if text.lower() not in report_lower
    ]
    failures += [
        f"report mentions '{text}'"
        for text in expect.report_excludes
        if text.lower() in report_lower
    ]

    return ScenarioResult(
        scenario_id=scenario.id,
        passed=not failures,
        tool_accuracy=tool_accuracy(set(expect.tools), picked, set(expect.allowed_extra_tools)),
        status=run["status"],
        failures=failures,
        picked_tools=sorted(picked),
        run_id=run.get("id"),
        llm_calls=metrics.get("llm_calls", 0),
        input_tokens=metrics.get("total_input_tokens", 0),
        output_tokens=metrics.get("total_output_tokens", 0),
        llm_latency_ms=metrics.get("total_latency_ms", 0.0),
        cost_usd=metrics.get("total_cost_usd", 0.0),
    )


def _tools(steps: list[dict[str, Any]], kind: str, status: str | None = None) -> set[str]:
    return {
        step["tool_name"]
        for step in steps
        if step["kind"] == kind and step.get("tool_name") and status in (None, step["status"])
    }
