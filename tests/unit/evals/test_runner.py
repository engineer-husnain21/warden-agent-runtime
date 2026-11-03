import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.schemas.role import Role
from evals import runner
from evals.runner import main, run_scenario, run_with_retries
from evals.scenario import Scenario
from evals.scenario_result import ScenarioResult
from tests.unit.evals.scenario_factory import APPROVED_STEPS, METRICS, make_scenario

KEYS = {role: f"key-{role.value}" for role in Role}
REPORT = "## Actions taken\n- Would create GitHub issue (dry-run, nothing was created): Timeouts"


class FakeWardenApi:
    """Scripted Warden API: the run pauses once for approval, then finishes."""

    def __init__(self, statuses: list[str], error: str | None = None) -> None:
        self._statuses: Iterator[str] = iter(statuses)
        self._status = "pending"
        self._error = error
        self.decisions: list[tuple[str, dict[str, Any], str]] = []
        self.created_by: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        path, key = request.url.path.removeprefix("/api/v1"), request.headers["X-API-Key"]
        if request.method == "POST" and path == "/agent-runs":
            self.created_by.append(key)
            return httpx.Response(202, json={"id": "r1", "status": "pending"})
        if request.method == "POST":
            self.decisions.append((path, json.loads(request.content), key))
            return httpx.Response(200, json={})
        if path == "/agent-runs/r1":
            self._status = next(self._statuses, self._status)
            return httpx.Response(
                200, json={"id": "r1", "status": self._status, "error": self._error}
            )
        if path == "/approvals":
            return httpx.Response(
                200, json=[{"id": "a1", "run_id": "r1"}, {"id": "a2", "run_id": "x"}]
            )
        if path.endswith("/steps"):
            return httpx.Response(200, json=APPROVED_STEPS)
        if path.endswith("/report"):
            return httpx.Response(200, json={"report": REPORT})
        return httpx.Response(200, json=METRICS)


def _client(api: FakeWardenApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(api.handle), base_url="http://test/api/v1"
    )


async def _no_sleep(_seconds: float) -> None:
    return None


async def test_run_scenario_when_run_pauses_approves_as_admin_and_scores() -> None:
    api = FakeWardenApi(["running", "awaiting_approval", "running", "completed"])

    async with _client(api) as client:
        result = await run_scenario(client, make_scenario(), KEYS, sleep=_no_sleep)

    assert result.passed, result.failures
    assert api.created_by == [KEYS[Role.OPERATOR]]
    assert api.decisions == [
        (
            "/approvals/a1/decisions",
            {"approved": True, "reason": "eval scenario decision"},
            KEYS[Role.ADMIN],
        )
    ]


async def test_run_scenario_when_scenario_expects_no_approval_rejects_and_fails() -> None:
    api = FakeWardenApi(["awaiting_approval", "completed"])

    async with _client(api) as client:
        result = await run_scenario(client, make_scenario(approval="none"), KEYS, sleep=_no_sleep)

    assert api.decisions[0][1]["approved"] is False
    assert "paused for approval, but the scenario expects no approval" in result.failures


async def test_run_with_retries_when_rate_limited_retries_then_gives_up() -> None:
    api = FakeWardenApi(["failed"], error="Groq returned 429 Too Many Requests")
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    async with _client(api) as client:
        result = await run_with_retries(
            client, make_scenario(), KEYS, retries=2, backoff_seconds=10, sleep=record_sleep
        )

    assert not result.passed
    assert result.attempts == 3
    assert waits == [10, 20]
    assert len(api.created_by) == 3


def _stub_suite(monkeypatch: pytest.MonkeyPatch, passed: list[bool]) -> None:
    """Replace the real app + LLM with canned results; main() still scores and writes reports."""

    async def fake_run(
        scenarios: list[Scenario], keys: dict[Role, str], concurrency: int
    ) -> list[ScenarioResult]:
        return [
            ScenarioResult(
                scenario_id=f"s{index}", passed=ok, tool_accuracy=1.0, status="completed"
            )
            for index, ok in enumerate(passed)
        ]

    monkeypatch.setattr(runner, "prepare_environment", lambda _work_dir: KEYS)
    monkeypatch.setattr(runner, "_run", fake_run)


def test_main_when_score_below_threshold_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_suite(monkeypatch, [True, False, False, True])  # success rate 0.5

    exit_code = main(["--threshold", "0.8", "--reports-dir", str(tmp_path)])

    assert exit_code == 1
    assert "gate **FAILED**" in (tmp_path / "latest.md").read_text(encoding="utf-8")


def test_main_when_scores_reach_threshold_exits_0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_suite(monkeypatch, [True, True, True, True, False])  # success rate 0.8

    assert main(["--threshold", "0.8", "--reports-dir", str(tmp_path)]) == 0
