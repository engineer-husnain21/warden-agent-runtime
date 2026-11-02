import pytest

from web.trace_format import decision_label, expander_title, trace_row


@pytest.mark.parametrize(
    ("approved", "expected"), [(True, "approved by ada"), (False, "rejected by ada")]
)
def test_decision_label_when_approval_decided_names_who_decided(
    approved: bool, expected: str
) -> None:
    step = {
        "kind": "approval",
        "policy_decision": None,
        "output": {"approved": approved, "decided_by": "ada", "reason": None},
    }

    assert decision_label(step) == expected


def test_decision_label_when_permission_check_shows_policy_decision() -> None:
    step = {"kind": "permission_check", "policy_decision": "needs_approval", "output": None}

    assert decision_label(step) == "needs_approval"


def test_decision_label_when_approval_still_waiting_shows_policy_decision() -> None:
    step = {
        "kind": "approval",
        "policy_decision": "needs_approval",
        "output": {"step": "Open an issue"},
    }

    assert decision_label(step) == "needs_approval"


PLAN_STEP = {
    "position": 0,
    "kind": "plan",
    "status": "succeeded",
    "agent": "planner",
    "tool_name": None,
    "policy_decision": None,
    "output": {"steps": []},
    "input_tokens": 600,
    "output_tokens": 380,
    "latency_ms": 1640.4,
    "cost_usd": 0.00032,
}


def test_trace_row_when_values_missing_shows_dashes() -> None:
    row = trace_row(PLAN_STEP)

    assert (row["tool"], row["decision"]) == ("—", "—")
    assert (row["agent"], row["tokens"], row["latency ms"]) == ("planner", 980, 1640)


@pytest.mark.parametrize(
    ("tool_name", "expected"),
    [(None, "#0 plan"), ("", "#0 plan"), ("warehouse.run_query", "#0 plan · warehouse.run_query")],
)
def test_expander_title_when_no_tool_has_no_trailing_separator(
    tool_name: str | None, expected: str
) -> None:
    assert expander_title({**PLAN_STEP, "tool_name": tool_name}) == expected
