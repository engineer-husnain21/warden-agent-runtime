import pytest

from app.core.config import Settings
from app.policies.tool_permission_policy import ToolPermissionPolicy
from app.schemas.policy_decision import PolicyDecision
from app.schemas.role import Role

ALLOW, DENY, APPROVE = (
    PolicyDecision.ALLOW,
    PolicyDecision.DENY,
    PolicyDecision.NEEDS_APPROVAL,
)

# Every tool the three MCP servers expose, against every role, with the default rules.
MATRIX = {
    "warehouse.list_tables": (ALLOW, ALLOW, ALLOW),
    "warehouse.describe_table": (ALLOW, ALLOW, ALLOW),
    "warehouse.run_query": (ALLOW, ALLOW, ALLOW),
    "github.list_issues": (ALLOW, ALLOW, ALLOW),
    "github.create_issue": (DENY, APPROVE, ALLOW),
    "notifier.list_outbox": (ALLOW, ALLOW, ALLOW),
    "notifier.send_notification": (DENY, APPROVE, ALLOW),
}
CASES = [
    (tool, role, expected)
    for tool, decisions in MATRIX.items()
    for role, expected in zip((Role.VIEWER, Role.OPERATOR, Role.ADMIN), decisions, strict=True)
]


@pytest.fixture
def policy() -> ToolPermissionPolicy:
    return ToolPermissionPolicy(Settings(_env_file=None).tool_permission_rules)  # type: ignore[call-arg]


@pytest.mark.parametrize(("tool", "role", "expected"), CASES)
def test_decide_when_default_rules_matches_role_matrix(
    policy: ToolPermissionPolicy, tool: str, role: Role, expected: PolicyDecision
) -> None:
    assert policy.decide(tool, role) is expected


def test_decide_when_operator_creates_issue_needs_approval(policy: ToolPermissionPolicy) -> None:
    assert policy.decide("github.create_issue", Role.OPERATOR) is APPROVE


def test_decide_when_viewer_calls_unknown_tool_denies(policy: ToolPermissionPolicy) -> None:
    assert policy.decide("shell.run", Role.VIEWER) is DENY


def test_decide_when_exact_rule_and_wildcard_exact_wins() -> None:
    policy = ToolPermissionPolicy({Role.VIEWER: {"github.*": DENY, "github.list_issues": ALLOW}})

    assert policy.decide("github.list_issues", Role.VIEWER) is ALLOW
    assert policy.decide("github.create_issue", Role.VIEWER) is DENY


def test_decide_when_role_has_no_rules_denies() -> None:
    assert ToolPermissionPolicy({}).decide("warehouse.run_query", Role.ADMIN) is DENY
