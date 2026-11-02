import pytest

from web.trace_format import decision_label


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
