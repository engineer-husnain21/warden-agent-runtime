from typing import Any

import httpx

from web.warden_api_error import WardenApiError

API_PREFIX = "/api/v1"
# Runs in these states can still change, so the home page keeps refreshing while any exist.
ACTIVE_STATUSES = frozenset({"pending", "running", "awaiting_approval"})


class WardenApiClient:
    """Small synchronous client for the Warden API (Streamlit scripts are synchronous)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=f"{base_url.strip().rstrip('/')}{API_PREFIX}",
            # Pasted keys often carry spaces or newlines, which are illegal in HTTP headers.
            headers={"X-API-Key": api_key.strip()},
            timeout=timeout_seconds,
            transport=transport,
        )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self._request("GET", "/agent-runs", params={"limit": limit})
        return result

    def create_run(self, task: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("POST", "/agent-runs", json={"task": task})
        return result

    def get_run(self, run_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/agent-runs/{run_id}")
        return result

    def get_steps(self, run_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self._request("GET", f"/agent-runs/{run_id}/steps")
        return result

    def get_report(self, run_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/agent-runs/{run_id}/report")
        return result

    def get_metrics(self, run_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/agent-runs/{run_id}/metrics")
        return result

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self._request("GET", "/approvals")
        return result

    def get_overview(self, limit: int = 50) -> dict[str, Any]:
        """Recent runs plus home-page totals. `active` is true while any run still needs the
        page to refresh (pending, running or waiting for approval).

        Total cost sums the per-run metrics of the listed runs (one request per run).
        """
        runs = self.list_runs(limit)
        statuses = [run["status"] for run in runs]
        total_cost = sum(self.get_metrics(run["id"])["total_cost_usd"] for run in runs)
        return {
            "runs": runs,
            "total_runs": len(runs),
            "awaiting_approval": statuses.count("awaiting_approval"),
            "completed": statuses.count("completed"),
            "total_cost_usd": total_cost,
            "status_counts": {status: statuses.count(status) for status in dict.fromkeys(statuses)},
            "active": any(status in ACTIVE_STATUSES for status in statuses),
        }

    def list_pending_approvals_with_context(self) -> list[dict[str, Any]]:
        """Pending approvals plus what a reviewer needs: the run's task, the requester's role
        and why the policy asked for a human (each run is fetched once)."""
        approvals = self.list_pending_approvals()
        runs: dict[str, dict[str, Any]] = {}
        enriched = []
        for approval in approvals:
            run_id = approval["run_id"]
            if run_id not in runs:
                runs[run_id] = self.get_run(run_id)
            run = runs[run_id]
            enriched.append(
                {
                    **approval,
                    "run_task": run["task"],
                    "requested_role": run["role"],
                    "policy_reason": (
                        f"The '{run['role']}' role may call {approval['tool_name']} only after "
                        "a human approves it."
                    ),
                }
            )
        return enriched

    def decide(self, approval_id: str, approved: bool, reason: str | None) -> dict[str, Any]:
        body = {"approved": approved, "reason": reason or None}
        result: dict[str, Any] = self._request(
            "POST", f"/approvals/{approval_id}/decisions", json=body
        )
        return result

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise WardenApiError(0, f"API not reachable: {error}") from error
        if response.is_error:
            raise WardenApiError(response.status_code, _error_message(response))
        return response.json()


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return str(error.get("message", ""))
    return str(body.get("detail", body)) if isinstance(body, dict) else str(body)
