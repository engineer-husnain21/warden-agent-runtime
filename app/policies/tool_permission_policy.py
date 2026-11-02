from collections.abc import Mapping

from app.schemas.policy_decision import PolicyDecision
from app.schemas.role import Role

ToolRules = Mapping[Role, Mapping[str, PolicyDecision]]


class ToolPermissionPolicy:
    """Decides allow / deny / needs_approval for one tool call by one role.

    Each role has rules keyed by tool pattern. The most specific match wins:
    exact name (`github.create_issue`) > server wildcard (`github.*`) > `*`.
    No match, or an unknown role, means DENY (fail closed).
    """

    def __init__(self, rules: ToolRules) -> None:
        self._rules = {role: dict(role_rules) for role, role_rules in rules.items()}

    def decide(self, tool: str, role: Role) -> PolicyDecision:
        role_rules = self._rules.get(role, {})
        server = tool.split(".", 1)[0]
        for pattern in (tool, f"{server}.*", "*"):
            if pattern in role_rules:
                return role_rules[pattern]
        return PolicyDecision.DENY
