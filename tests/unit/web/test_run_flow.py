from typing import Any

from web.run_flow import APPROVAL_COLOR, build_run_flow_dot


def _step(position: int, kind: str, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "position": position,
        "kind": kind,
        "status": status,
        "tool_name": None,
        "policy_decision": None,
        "output": None,
        **extra,
    }


STEPS = [
    _step(0, "plan", "succeeded"),
    _step(1, "tool_call", "failed", tool_name="warehouse.run_query"),
    _step(
        2,
        "approval",
        "succeeded",
        tool_name="github.create_issue",
        output={"approved": True, "decided_by": "ada"},
    ),
]


def test_build_run_flow_dot_when_steps_given_chains_them_from_task_to_status() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    assert dot.startswith("digraph run {")
    for edge in ("start -> s0;", "s0 -> s1;", "s1 -> s2;", "s2 -> end;"):
        assert edge in dot
    assert 'label="completed"' in dot


def test_build_run_flow_dot_when_step_failed_colours_it_red() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    failed_node = next(line for line in dot.splitlines() if line.strip().startswith("s1 ["))
    assert 'color="#F04438"' in failed_node
    assert "warehouse.run_query" in failed_node


def test_build_run_flow_dot_when_approval_highlights_it_with_decider() -> None:
    dot = build_run_flow_dot(STEPS, "completed")

    approval_node = next(line for line in dot.splitlines() if line.strip().startswith("s2 ["))
    assert f'color="{APPROVAL_COLOR}"' in approval_node
    assert "peripheries=2" in approval_node
    assert "approved by ada" in approval_node


def test_build_run_flow_dot_when_no_steps_links_task_to_status() -> None:
    dot = build_run_flow_dot([], "pending")

    assert "start -> end;" in dot
    assert 'label="pending"' in dot
