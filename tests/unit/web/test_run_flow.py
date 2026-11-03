from typing import Any

from web import theme
from web.run_flow import APPROVAL_COLOR, build_run_flow_dot, group_steps


def _step(position: int, kind: str, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "position": position,
        "step_index": None,
        "kind": kind,
        "status": status,
        "tool_name": None,
        "policy_decision": None,
        "output": None,
        **extra,
    }


QUERY = "warehouse.run_query"
ISSUE = "github.create_issue"
STEPS = [
    _step(0, "plan", "succeeded", output={"steps": [{}, {}]}),
    _step(1, "tool_selection", "succeeded", step_index=0, tool_name=QUERY),
    _step(2, "permission_check", "succeeded", step_index=0, tool_name=QUERY),
    _step(3, "tool_call", "failed", step_index=0, tool_name=QUERY),
    _step(4, "review", "failed", step_index=0, tool_name=QUERY),
    _step(5, "tool_selection", "succeeded", step_index=1, tool_name=ISSUE),
    _step(
        6,
        "permission_check",
        "awaiting_approval",
        step_index=1,
        tool_name=ISSUE,
        policy_decision="needs_approval",
    ),
    _step(
        7,
        "approval",
        "succeeded",
        step_index=1,
        tool_name=ISSUE,
        output={"approved": True, "decided_by": "ada"},
    ),
    _step(8, "tool_call", "succeeded", step_index=1, tool_name=ISSUE),
    _step(9, "review", "succeeded", step_index=1, tool_name=ISSUE),
    _step(10, "report", "succeeded", output={"report": "..."}),
]


def _node(dot: str, name: str) -> str:
    return next(line for line in dot.splitlines() if line.strip().startswith(f"{name} ["))


def test_build_run_flow_dot_when_steps_given_draws_top_to_bottom() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    assert dot.startswith("digraph run {")
    assert "rankdir=TB" in dot


def test_build_run_flow_dot_when_steps_given_draws_one_node_per_plan_step() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    edges = ("start -> plan_0;", "plan_0 -> s0;", "s0 -> s1;", "s1 -> report_10;", "-> end;")
    for edge in edges:
        assert edge in dot
    assert dot.count(" -> ") == 5
    assert "Plan · 2 steps" in _node(dot, "plan_0")
    assert 'label="completed"' in dot


def test_build_run_flow_dot_when_step_failed_colours_it_red() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    failed_node = _node(dot, "s0")
    assert f'color="{theme.RED}"' in failed_node
    assert "Step 1: warehouse.run_query - failed" in failed_node


def test_build_run_flow_dot_when_approval_highlights_it_with_decider() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    approval_node = _node(dot, "s1")
    assert "Step 2: github.create_issue - approved by ada" in approval_node
    assert f'color="{APPROVAL_COLOR}"' in approval_node
    assert f'fillcolor="{theme.AMBER}88"' in approval_node
    assert 'style="rounded,filled,bold"' in approval_node
    assert "peripheries=2" in approval_node


def test_build_run_flow_dot_when_waiting_for_approval_says_waiting() -> None:
    # While paused, the service records an approval event that has no decision yet.
    paused = _step(
        7,
        "approval",
        "awaiting_approval",
        step_index=1,
        tool_name=ISSUE,
        policy_decision="needs_approval",
        output={"step": "Open an issue"},
    )

    dot = build_run_flow_dot([*STEPS[:7], paused], "awaiting_approval")

    node = _node(dot, "s1")
    assert "Step 2: github.create_issue - awaiting approval" in node
    assert "peripheries=2" in node
    assert "s1 -> end;" in dot


def test_build_run_flow_dot_when_no_steps_links_task_to_status() -> None:
    dot = build_run_flow_dot([], "pending")

    assert "start -> end;" in dot
    assert 'label="pending"' in dot


def test_build_run_flow_dot_when_steps_given_fills_nodes_with_kind_colours() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    assert f'fillcolor="{theme.PURPLE}55"' in _node(dot, "plan_0")
    assert f'fillcolor="{theme.PINK}55"' in _node(dot, "s0")
    assert f'fillcolor="{theme.GREEN}55"' in _node(dot, "report_10")


def test_build_run_flow_dot_when_step_retried_counts_attempts() -> None:
    retried = [
        _step(0, "tool_selection", "succeeded", step_index=0, tool_name=QUERY),
        _step(1, "review", "failed", step_index=0, tool_name=QUERY),
        _step(2, "tool_selection", "succeeded", step_index=0, tool_name=QUERY),
        _step(3, "review", "succeeded", step_index=0, tool_name=QUERY),
    ]

    node = _node(build_run_flow_dot(retried, "completed"), "s0")

    assert "Step 1: warehouse.run_query - succeeded\\n2 attempts" in node


def test_group_steps_when_step_index_missing_infers_it_and_keeps_retries_together() -> None:
    legacy = [{**step, "step_index": None} for step in STEPS]
    legacy.insert(5, _step(4, "tool_selection", "succeeded", tool_name=QUERY))  # retry

    keys = [key for key, _ in group_steps(legacy)]

    assert keys == ["plan", "s0", "s1", "report"]
