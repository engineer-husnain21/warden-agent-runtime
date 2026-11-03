from typing import Any

from evals.scenario import Scenario


def make_scenario(**overrides: Any) -> Scenario:
    data: dict[str, Any] = {
        "id": "github_open_issue",
        "description": "Opens an issue after approval",
        "task": "Open a GitHub issue about payment timeouts",
        "role": "operator",
        "approval": "approve",
        "expect": {
            "tools": ["github.create_issue"],
            "executed": ["github.create_issue"],
            "report_contains": ["Would create GitHub issue"],
        },
    }
    data.update(overrides)
    return Scenario.model_validate(data)


def step(kind: str, status: str = "succeeded", tool: str | None = None) -> dict[str, Any]:
    return {"kind": kind, "status": status, "tool_name": tool}


ISSUE = "github.create_issue"
APPROVED_STEPS = [
    step("plan"),
    step("tool_selection", tool=ISSUE),
    step("permission_check", "awaiting_approval", ISSUE),
    step("approval", tool=ISSUE),
    step("tool_call", tool=ISSUE),
    step("review", tool=ISSUE),
    step("report"),
]
METRICS = {
    "llm_calls": 4,
    "total_input_tokens": 3000,
    "total_output_tokens": 500,
    "total_latency_ms": 4200.0,
    "total_cost_usd": 0.00075,
}
