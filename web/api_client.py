from typing import Any

import httpx

from web.warden_api_error import WardenApiError

API_PREFIX = "/api/v1"


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
