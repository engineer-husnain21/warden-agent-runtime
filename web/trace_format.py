"""How trace rows are shown in the console. Pure functions, so they are easy to test."""

from html import escape
from typing import Any

from web.console_layout import status_pill
from web.theme import kind_color


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


KIND_ICONS = {
    "plan": "🧭",
    "tool_selection": "🎯",
    "permission_check": "🛡️",
    "approval": "✋",
    "tool_call": "🔧",
    "review": "🔍",
    "report": "📝",
}
KIND_TITLES = {
    "plan": "Plan",
    "tool_selection": "Select tool",
    "permission_check": "Permission check",
    "approval": "Approval",
    "tool_call": "Tool call",
    "review": "Review",
    "report": "Report",
}


def timeline_html(steps: list[dict[str, Any]]) -> str:
    """The trace as a vertical timeline (HTML; every value from the API is escaped)."""
    items = [_timeline_item(step) for step in steps]
    return f'<div class="warden-timeline">{"".join(items)}</div>'


def _timeline_item(step: dict[str, Any]) -> str:
    kind = step["kind"]
    title = escape(KIND_TITLES.get(kind, kind))
    tool = (
        f'<span class="tl-tool">{escape(step["tool_name"])}</span>' if step.get("tool_name") else ""
    )
    meta = [escape(str(part)) for part in (step.get("agent"), decision_label(step)) if part]
    tokens = step["input_tokens"] + step["output_tokens"]
    if tokens:
        meta.append(
            f"{tokens:,} tokens · {step['latency_ms'] / 1000:.1f} s · ${step['cost_usd']:.5f}"
        )
    pill = status_pill(step["status"])
    return (
        f'<div class="tl-item" style="--k: {kind_color(kind)}">'
        f'<div class="tl-icon">{KIND_ICONS.get(kind, "•")}</div>'
        '<div class="tl-body">'
        f'<div class="tl-title">#{step["position"]} {title} {tool} {pill}</div>'
        f'<div class="tl-meta">{" · ".join(meta) or EMPTY_CELL}</div>'
        "</div></div>"
    )
