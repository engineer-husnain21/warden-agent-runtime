import pytest

from app.core.config import Settings
from app.policies.step_retry_policy import StepRetryPolicy
from app.schemas.policy_decision import PolicyDecision

ALLOW = PolicyDecision.ALLOW
NEEDS_APPROVAL = PolicyDecision.NEEDS_APPROVAL


@pytest.fixture
def policy() -> StepRetryPolicy:
    return StepRetryPolicy(Settings(_env_file=None).read_only_tools)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "tool", ["warehouse.run_query", "warehouse.list_tables", "github.list_issues"]
)
def test_may_retry_when_read_only_tool_succeeded_returns_true(
    policy: StepRetryPolicy, tool: str
) -> None:
    assert policy.may_retry(tool, call_succeeded=True, decision=ALLOW) is True


@pytest.mark.parametrize("tool", ["github.create_issue", "notifier.send_notification"])
@pytest.mark.parametrize("decision", [ALLOW, NEEDS_APPROVAL])
def test_may_retry_when_write_tool_succeeded_returns_false(
    policy: StepRetryPolicy, tool: str, decision: PolicyDecision
) -> None:
    assert policy.may_retry(tool, call_succeeded=True, decision=decision) is False


def test_may_retry_when_write_tool_call_failed_returns_true(policy: StepRetryPolicy) -> None:
    assert policy.may_retry("github.create_issue", call_succeeded=False, decision=NEEDS_APPROVAL)


def test_may_retry_when_tool_unlisted_and_succeeded_returns_false(policy: StepRetryPolicy) -> None:
    assert policy.may_retry("billing.refund", call_succeeded=True, decision=ALLOW) is False


def test_may_retry_when_read_only_tool_needed_approval_returns_false() -> None:
    policy = StepRetryPolicy(["github.*"])

    assert (
        policy.may_retry("github.list_issues", call_succeeded=True, decision=NEEDS_APPROVAL)
        is False
    )
