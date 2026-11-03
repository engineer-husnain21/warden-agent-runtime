"""Writes the eval results as JSON (for tools / CI artifacts) and Markdown (for people)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from evals.eval_summary import EvalSummary
from evals.scenario_result import ScenarioResult


def gate_passes(summary: EvalSummary, threshold: float) -> bool:
    """CI gate: both task success rate and tool-call accuracy must reach the threshold."""
    return (
        summary.scenarios > 0
        and summary.success_rate >= threshold
        and summary.tool_accuracy >= threshold
    )


def write_reports(
    results: list[ScenarioResult],
    summary: EvalSummary,
    reports_dir: Path,
    threshold: float,
    llm: str,
) -> tuple[Path, Path]:
    """Write `eval-<timestamp>.json` and `.md` plus `latest.*` copies; return the latest paths."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "llm": llm,
        "threshold": threshold,
        "gate_passed": gate_passes(summary, threshold),
        "summary": summary.model_dump(),
        "results": [result.model_dump() for result in results],
    }
    json_text = json.dumps(payload, indent=2)
    markdown = render_markdown(results, summary, threshold, llm, now)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    for name in (f"eval-{stamp}", "latest"):
        (reports_dir / f"{name}.json").write_text(json_text, encoding="utf-8")
        (reports_dir / f"{name}.md").write_text(markdown, encoding="utf-8")
    return reports_dir / "latest.json", reports_dir / "latest.md"


def render_markdown(
    results: list[ScenarioResult],
    summary: EvalSummary,
    threshold: float,
    llm: str,
    now: datetime,
) -> str:
    verdict = "PASSED" if gate_passes(summary, threshold) else "FAILED"
    success = f"{summary.success_rate:.2f} ({summary.passed}/{summary.scenarios})"
    lines = [
        "# Warden eval report",
        "",
        f"{now:%Y-%m-%d %H:%M} UTC · LLM `{llm}` · gate **{verdict}** (threshold {threshold:.2f})",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Task success rate | {success} |",
        f"| Tool-call accuracy | {summary.tool_accuracy:.2f} |",
        f"| Avg tokens per run | {summary.avg_tokens_per_run:,.0f} |",
        f"| Avg LLM latency per run | {summary.avg_llm_latency_seconds:.1f} s |",
        f"| Avg cost per run | ${summary.avg_cost_usd:.5f} |",
        f"| Total cost | ${summary.total_cost_usd:.4f} |",
        "",
        "| Scenario | Result | Tool acc. | Tokens | LLM s | Cost | Tries | Failures |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        tokens = result.input_tokens + result.output_tokens
        failures = "; ".join(result.failures).replace("|", "/") or "—"
        lines.append(
            f"| {result.scenario_id} | {'pass' if result.passed else '**fail**'} "
            f"| {result.tool_accuracy:.2f} | {tokens:,} | {result.llm_latency_ms / 1000:.1f} "
            f"| ${result.cost_usd:.5f} | {result.attempts} | {failures} |"
        )
    return "\n".join(lines) + "\n"
