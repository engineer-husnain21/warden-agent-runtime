"""Eval runner: runs every scenario against the in-process API with the real LLM and scores it.

Usage: `uv run python -m evals.runner [--threshold 0.8] [--only id1,id2] [--concurrency 2]`
Exits 1 when task success rate or tool-call accuracy is below the threshold.
"""

import argparse
import asyncio
import os
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.schemas.role import Role
from evals.eval_environment import eval_client, prepare_environment
from evals.eval_summary import EvalSummary
from evals.report_writer import gate_passes, write_reports
from evals.scenario import Scenario
from evals.scenario_loader import load_scenarios
from evals.scenario_result import ScenarioResult
from evals.scoring import score_run

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
SETTLED = {"awaiting_approval", "completed", "failed"}
MAX_APPROVALS = 3
RATE_LIMIT_MARKERS = ("429", "rate limit", "rate_limit", "too many requests")

Sleep = Callable[[float], Awaitable[None]]
logger = get_logger("evals.runner")


async def run_scenario(
    client: httpx.AsyncClient,
    scenario: Scenario,
    keys: dict[Role, str],
    *,
    timeout_seconds: float = 300.0,
    poll_seconds: float = 1.0,
    sleep: Sleep = asyncio.sleep,
) -> ScenarioResult:
    """Start the run as the scenario's role, answer approvals as admin, then score the result."""
    caller = {"X-API-Key": keys[scenario.role]}
    admin = {"X-API-Key": keys[Role.ADMIN]}
    started = time.monotonic()
    response = await client.post("/agent-runs", json={"task": scenario.task}, headers=caller)
    response.raise_for_status()
    run_id = response.json()["id"]
    deadline = started + timeout_seconds
    notes: list[str] = []
    for _ in range(MAX_APPROVALS + 1):
        run = await _wait_until_settled(client, run_id, caller, deadline, poll_seconds, sleep)
        if run["status"] not in SETTLED:
            notes.append(f"timed out after {timeout_seconds:.0f}s")
            break
        if run["status"] != "awaiting_approval":
            break
        if scenario.approval == "none":
            notes.append("paused for approval, but the scenario expects no approval")
        await _decide_pending(client, run_id, admin, approve=scenario.approval == "approve")
    else:
        notes.append(f"asked for approval more than {MAX_APPROVALS} times")

    steps = await _get(client, f"/agent-runs/{run_id}/steps", caller)
    report = (await _get(client, f"/agent-runs/{run_id}/report", caller)).get("report") or ""
    metrics = await _get(client, f"/agent-runs/{run_id}/metrics", caller)
    result = score_run(scenario, run, steps, report, metrics, notes)
    return result.model_copy(update={"duration_seconds": round(time.monotonic() - started, 1)})


async def run_with_retries(
    client: httpx.AsyncClient,
    scenario: Scenario,
    keys: dict[Role, str],
    *,
    retries: int = 2,
    backoff_seconds: float = 30.0,
    sleep: Sleep = asyncio.sleep,
    **options: Any,
) -> ScenarioResult:
    """Run again (after a growing pause) only when a failure was caused by an LLM rate limit."""
    for attempt in range(1, retries + 2):
        result = await run_scenario(client, scenario, keys, sleep=sleep, **options)
        if result.passed or attempt > retries or not _rate_limited(result):
            return result.model_copy(update={"attempts": attempt})
        delay = backoff_seconds * 2 ** (attempt - 1)
        logger.warning("%s hit the LLM rate limit; retrying in %.0fs", scenario.id, delay)
        await sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


async def run_suite(
    client: httpx.AsyncClient,
    scenarios: list[Scenario],
    keys: dict[Role, str],
    concurrency: int = 2,
) -> list[ScenarioResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(scenario: Scenario) -> ScenarioResult:
        async with semaphore:
            result = await run_with_retries(client, scenario, keys)
        verdict = "PASS" if result.passed else "FAIL"
        logger.info("%s %s %s", verdict, scenario.id, "; ".join(result.failures))
        return result

    return list(await asyncio.gather(*(run_one(scenario) for scenario in scenarios)))


async def _wait_until_settled(
    client: httpx.AsyncClient,
    run_id: str,
    headers: dict[str, str],
    deadline: float,
    poll_seconds: float,
    sleep: Sleep,
) -> dict[str, Any]:
    while True:
        run: dict[str, Any] = await _get(client, f"/agent-runs/{run_id}", headers)
        if run["status"] in SETTLED or time.monotonic() > deadline:
            return run
        await sleep(poll_seconds)


async def _decide_pending(
    client: httpx.AsyncClient, run_id: str, admin: dict[str, str], *, approve: bool
) -> None:
    for approval in await _get(client, "/approvals", admin):
        if approval["run_id"] == run_id:
            body = {"approved": approve, "reason": "eval scenario decision"}
            response = await client.post(
                f"/approvals/{approval['id']}/decisions", json=body, headers=admin
            )
            response.raise_for_status()


async def _get(client: httpx.AsyncClient, path: str, headers: dict[str, str]) -> Any:
    response = await client.get(path, headers=headers)
    response.raise_for_status()
    return response.json()


def _rate_limited(result: ScenarioResult) -> bool:
    text = " ".join(result.failures).lower()
    return any(marker in text for marker in RATE_LIMIT_MARKERS)


async def _run(
    scenarios: list[Scenario], keys: dict[Role, str], concurrency: int
) -> list[ScenarioResult]:
    async with eval_client() as client:
        return await run_suite(client, scenarios, keys, concurrency)


def main(argv: list[str] | None = None) -> int:
    """Run the suite, write the reports and return 1 when the scores are below the threshold."""
    parser = argparse.ArgumentParser(description="Run the Warden eval suite (real LLM).")
    parser.add_argument("--only", default="", help="comma-separated scenario ids to run")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--threshold", type=float, default=float(os.environ.get("EVAL_THRESHOLD", "0.8"))
    )
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)
    configure_logging("INFO")
    scenarios = load_scenarios()
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [scenario for scenario in scenarios if scenario.id in wanted]
    with tempfile.TemporaryDirectory(prefix="warden-evals-", ignore_cleanup_errors=True) as work:
        keys = prepare_environment(Path(work))
        results = asyncio.run(_run(scenarios, keys, args.concurrency))

    settings = get_settings()
    llm = f"{settings.llm_provider}:{_model_name(settings)}"
    summary = EvalSummary.from_results(results)
    _, markdown_path = write_reports(results, summary, args.reports_dir, args.threshold, llm)
    logger.info(
        "success rate %.2f (%d/%d), tool-call accuracy %.2f, avg %.0f tokens, $%.5f per run",
        summary.success_rate,
        summary.passed,
        summary.scenarios,
        summary.tool_accuracy,
        summary.avg_tokens_per_run,
        summary.avg_cost_usd,
    )
    logger.info("report: %s", markdown_path)
    if gate_passes(summary, args.threshold):
        return 0
    logger.error("eval gate failed: scores below the %.2f threshold", args.threshold)
    return 1


def _model_name(settings: Settings) -> str:
    return settings.gemini_model if settings.llm_provider == "gemini" else settings.groq_model


if __name__ == "__main__":
    raise SystemExit(main())
