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
