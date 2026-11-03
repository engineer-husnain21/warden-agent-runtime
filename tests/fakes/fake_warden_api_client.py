from typing import Any

from web.warden_api_error import WardenApiError

RUN = {
    "id": "r1",
    "task": "Find failed orders",
    "requested_by": "oscar",
    "role": "operator",
    "status": "awaiting_approval",
    "error": None,
    "created_at": "2026-11-02T09:00:00Z",
    "updated_at": "2026-11-02T09:00:05Z",
    "completed_at": None,
}


class FakeWardenApiClient:
    """Stands in for WardenApiClient in Streamlit AppTests; records calls."""

    def __init__(self, fail_with: str | None = None) -> None:
        self.fail_with = fail_with
        self.created: list[str] = []
        self.decisions: list[tuple[str, bool, str | None]] = []

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        if self.fail_with:
            raise WardenApiError(503, self.fail_with)
        return [RUN]

    def create_run(self, task: str) -> dict[str, Any]:
        self.created.append(task)
        return {**RUN, "id": "r2", "status": "pending", "task": task}

    def get_run(self, run_id: str) -> dict[str, Any]:
        return RUN

    def get_steps(self, run_id: str) -> list[dict[str, Any]]:
        return [
            {
                "position": 0,
                "step_index": None,
                "kind": "plan",
                "status": "succeeded",
                "agent": "planner",
                "tool_name": None,
                "tool_arguments": None,
                "output": {"steps": []},
                "policy_decision": None,
                "input_tokens": 600,
                "output_tokens": 380,
                "latency_ms": 1640.0,
                "cost_usd": 0.00032,
                "created_at": "2026-11-02T09:00:01Z",
            }
        ]

    def get_report(self, run_id: str) -> dict[str, Any]:
        return {"run_id": run_id, "status": "completed", "report": "## Summary\nAll good."}

    def get_metrics(self, run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "steps": [],
            "llm_calls": 6,
            "total_input_tokens": 4700,
            "total_output_tokens": 1450,
            "total_latency_ms": 6200.0,
            "total_cost_usd": 0.00157,
        }

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "a1",
                "run_id": "r1",
                "step_position": 1,
                "tool_name": "github.create_issue",
                "tool_arguments": {"title": "Top 3 failure causes"},
                "requested_by": "oscar",
                "status": "pending",
                "decided_by": None,
                "decision_reason": None,
                "created_at": "2026-11-02T09:00:04Z",
                "decided_at": None,
            }
        ]

    def get_overview(self, limit: int = 50) -> dict[str, Any]:
        runs = self.list_runs(limit)
        return {
            "runs": runs,
            "total_runs": len(runs),
            "awaiting_approval": 1,
            "completed": 0,
            "total_cost_usd": 0.00157,
            "status_counts": {"awaiting_approval": 1},
            "active": True,
        }

    def list_pending_approvals_with_context(self) -> list[dict[str, Any]]:
        return [
            {
                **approval,
                "run_task": RUN["task"],
                "requested_role": RUN["role"],
                "policy_reason": "The 'operator' role may call github.create_issue only after "
                "a human approves it.",
            }
            for approval in self.list_pending_approvals()
        ]

    def decide(self, approval_id: str, approved: bool, reason: str | None) -> dict[str, Any]:
        self.decisions.append((approval_id, approved, reason))
        return {"id": approval_id, "status": "approved" if approved else "rejected"}
