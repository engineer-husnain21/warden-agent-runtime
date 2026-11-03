"""The run as a top-to-bottom flow chart (Graphviz DOT), for `st.graphviz_chart`.

One node per plan step: its sub-events (select, permission, approval, tool call, review and
any retries) are grouped by `step_index`. Plan and report get their own nodes. Nodes are
outlined in the status colour of their last event; approval steps are amber with a bold
double border.
"""

from typing import Any

from web import theme
from web.trace_format import decision_label

APPROVAL_COLOR = theme.AMBER
_RUN_LEVEL_KINDS = {"plan", "report"}
_MUTED = theme.MUTED
_SURFACE = theme.SURFACE
_TEXT = theme.TEXT
_FILL_ALPHA = "55"  # ~33 % opacity: vivid but keeps the white labels readable
_APPROVAL_ALPHA = "88"

Group = list[dict[str, Any]]


def group_steps(steps: list[dict[str, Any]]) -> list[tuple[str, Group]]:
    """Consecutive events of the same plan step become one group, keyed "plan", "s<index>"
    or "report". Runs recorded before `step_index` was stored fall back to inferring it:
    a tool selection starts a new step unless it retries one after a failed review."""
    groups: list[tuple[str, Group]] = []
    inferred = -1
    previous: dict[str, Any] | None = None
    for step in steps:
        kind = step["kind"]
        if kind in _RUN_LEVEL_KINDS:
            key = kind
        else:
            index = step.get("step_index")
            if index is None:
                retry = previous is not None and _is_failed_review(previous)
                if (kind == "tool_selection" and not retry) or inferred < 0:
                    inferred += 1
                index = inferred
            else:
                inferred = index
            key = f"s{index}"
        if groups and groups[-1][0] == key:
            groups[-1][1].append(step)
        else:
            groups.append((key, [step]))
        previous = step
    return groups


def build_run_flow_dot(steps: list[dict[str, Any]], run_status: str) -> str:
    lines = [
        "digraph run {",
        '  graph [rankdir=TB, bgcolor="transparent", nodesep=0.3, ranksep=0.3, pad=0.2];',
        f'  node [shape=box, style="rounded,filled", fontname="Inter", fontsize=12,'
        f' width=3.6, height=0.5, margin="0.2,0.08", fillcolor="{_SURFACE}",'
        f' fontcolor="{_TEXT}", color="#262A33", penwidth=1.2];',
        '  edge [color="#3A3F4B", arrowsize=0.6];',
        f'  start [label="Task", shape=circle, fixedsize=true, width=0.6, color="{_MUTED}"];',
    ]
    previous = "start"
    for key, group in group_steps(steps):
        node = f"{key}_{group[0]['position']}" if key in _RUN_LEVEL_KINDS else key
        lines.append(f"  {node} [{_node_attributes(key, group)}];")
        lines.append(f"  {previous} -> {node};")
        previous = node
    end_color = theme.status_color(run_status)
    lines.append(
        f'  end [label="{_quote(run_status.replace("_", " "))}", shape=box, width=1.6, '
        f'color="{end_color}", fontcolor="{end_color}", fillcolor="{end_color}22"];'
    )
    lines.append(f"  {previous} -> end;")
    lines.append("}")
    return "\n".join(lines)


def _node_attributes(key: str, group: Group) -> str:
    last = group[-1]
    outline = theme.status_color(last["status"])
    if key in _RUN_LEVEL_KINDS:
        label = _quote(_run_level_label(group[0]))
        fill = theme.kind_color(key)
        return f'label="{label}", color="{outline}", fillcolor="{fill}{_FILL_ALPHA}"'
    label = _quote(_step_label(int(key[1:]), group))
    if not _needs_approval(group):
        fill = theme.kind_color("tool_call")
        return f'label="{label}", color="{outline}", fillcolor="{fill}{_FILL_ALPHA}"'
    # Graphviz has no glow; a bold double amber border reads as one on the dark background.
    return (
        f'label="{label}", color="{APPROVAL_COLOR}", fillcolor="{APPROVAL_COLOR}{_APPROVAL_ALPHA}",'
        ' style="rounded,filled,bold", penwidth=2.6, peripheries=2, fontcolor="#FFFFFF"'
    )


def _run_level_label(step: dict[str, Any]) -> str:
    if step["kind"] != "plan":
        return "Report"
    planned = len((step.get("output") or {}).get("steps", []))
    return f"Plan · {planned} step{'' if planned == 1 else 's'}"


def _step_label(index: int, group: Group) -> str:
    """'Step 2: github.create_issue - approved by ada' (+ a second line when it was retried)."""
    tools = [step["tool_name"] for step in group if step.get("tool_name")]
    title = f"Step {index + 1}: {tools[-1] if tools else 'no tool selected'}"
    approval = next((step for step in reversed(group) if step["kind"] == "approval"), None)
    if approval is not None:
        outcome = decision_label(approval) or "waiting"
    else:
        outcome = group[-1]["status"].replace("_", " ")
    attempts = sum(step["kind"] == "tool_selection" for step in group)
    retries = f"\\n{attempts} attempts" if attempts > 1 else ""
    return f"{title} - {outcome}{retries}"


def _needs_approval(group: Group) -> bool:
    return any(
        step["kind"] == "approval" or step.get("policy_decision") == "needs_approval"
        for step in group
    )


def _is_failed_review(step: dict[str, Any]) -> bool:
    return bool(step["kind"] == "review" and step["status"] == "failed")


def _quote(text: str) -> str:
    return text.replace('"', '\\"')
