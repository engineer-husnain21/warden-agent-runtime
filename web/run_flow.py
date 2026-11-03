"""The run as a left-to-right flow chart (Graphviz DOT), for `st.graphviz_chart`.

Nodes are filled with their step kind's colour and outlined in their status colour;
approval steps are amber with a bold double border.
"""

from typing import Any

from web import theme
from web.trace_format import decision_label

KIND_LABELS = {
    "plan": "Plan",
    "tool_selection": "Select tool",
    "permission_check": "Permission",
    "approval": "Approval",
    "tool_call": "Tool call",
    "review": "Review",
    "report": "Report",
}
APPROVAL_COLOR = theme.AMBER
_MUTED = theme.MUTED
_SURFACE = theme.SURFACE
_TEXT = theme.TEXT
_FILL_ALPHA = "55"  # ~33 % opacity: vivid but keeps the white labels readable
_APPROVAL_ALPHA = "88"


def build_run_flow_dot(steps: list[dict[str, Any]], run_status: str) -> str:
    lines = [
        "digraph run {",
        '  graph [rankdir=LR, bgcolor="transparent", nodesep=0.25, ranksep=0.3, pad=0.15];',
        f'  node [shape=box, style="rounded,filled", fontname="Inter", fontsize=11,'
        f' fillcolor="{_SURFACE}", fontcolor="{_TEXT}", color="#262A33", penwidth=1.2];',
        '  edge [color="#3A3F4B", arrowsize=0.6];',
        f'  start [label="Task", shape=circle, fixedsize=true, width=0.55, color="{_MUTED}"];',
    ]
    previous = "start"
    for step in steps:
        node = f"s{step['position']}"
        lines.append(f"  {node} [{_node_attributes(step)}];")
        lines.append(f"  {previous} -> {node};")
        previous = node
    end_color = theme.status_color(run_status)
    lines.append(
        f'  end [label="{_quote(run_status.replace("_", " "))}", shape=box, '
        f'color="{end_color}", fontcolor="{end_color}", fillcolor="{end_color}22"];'
    )
    lines.append(f"  {previous} -> end;")
    lines.append("}")
    return "\n".join(lines)


def _node_attributes(step: dict[str, Any]) -> str:
    """Fill = the step kind's colour; outline = the step status (so failures still stand out)."""
    fill = theme.kind_color(step["kind"])
    outline = theme.status_color(step["status"])
    label_lines = [KIND_LABELS.get(step["kind"], step["kind"])]
    if step.get("tool_name"):
        label_lines.append(step["tool_name"])
    if step["kind"] == "approval":
        label_lines.append(decision_label(step) or "waiting")
        outline = APPROVAL_COLOR
    label = _quote("\\n".join(label_lines))
    if step["kind"] != "approval":
        return f'label="{label}", color="{outline}", fillcolor="{fill}{_FILL_ALPHA}"'
    # Graphviz has no glow; a bold double amber border reads as one on the dark background.
    return (
        f'label="{label}", color="{outline}", fillcolor="{APPROVAL_COLOR}{_APPROVAL_ALPHA}",'
        ' style="rounded,filled,bold", penwidth=2.6, peripheries=2, fontcolor="#FFFFFF"'
    )


def _quote(text: str) -> str:
    return text.replace('"', '\\"')
