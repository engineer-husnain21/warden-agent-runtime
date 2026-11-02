"""How trace rows are shown in the console. Pure functions, so they are easy to test."""

from typing import Any


def decision_label(step: dict[str, Any]) -> str | None:
    """Approval rows show the human decision ("approved by ada"); others the policy decision."""
    output = step.get("output") or {}
    if step.get("kind") == "approval" and "approved" in output:
        verb = "approved" if output["approved"] else "rejected"
        return f"{verb} by {output.get('decided_by') or 'unknown'}"
    decision: str | None = step.get("policy_decision")
    return decision


EMPTY_CELL = "—"


def cell(value: Any) -> Any:
    """Empty values show as a dash instead of "None"."""
    return EMPTY_CELL if value is None or value == "" else value


def expander_title(step: dict[str, Any]) -> str:
    parts = [f"#{step['position']} {step['kind']}"]
    if step.get("tool_name"):
        parts.append(step["tool_name"])
    return " · ".join(parts)


def trace_row(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "#": step["position"],
        "kind": step["kind"],
        "status": step["status"],
        "agent": cell(step.get("agent")),
        "tool": cell(step.get("tool_name")),
        "decision": cell(decision_label(step)),
        "tokens": step["input_tokens"] + step["output_tokens"],
        "latency ms": round(step["latency_ms"]),
        "cost $": round(step["cost_usd"], 6),
    }
