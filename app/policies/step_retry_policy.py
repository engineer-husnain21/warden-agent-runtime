from collections.abc import Iterable

from app.schemas.policy_decision import PolicyDecision


class StepRetryPolicy:
    """Decides whether a step may be retried after its reviewer rejected the result.

    A write that already ran must never run again: a retry would repeat its side effect (a
    second issue, a second message), even when a human approves each call. So:
    - the tool call failed -> retry (nothing happened yet);
    - the call needed approval -> never retry, it is a write;
    - otherwise retry only tools listed as read-only (`server.tool`, `server.*` or `*`).
    Unlisted tools count as writes (fail safe).
    """

    def __init__(self, read_only_tools: Iterable[str]) -> None:
        self._read_only = set(read_only_tools)

    def may_retry(self, tool: str, call_succeeded: bool, decision: PolicyDecision) -> bool:
        if not call_succeeded:
            return True
        if decision is PolicyDecision.NEEDS_APPROVAL:
            return False
        return self.is_read_only(tool)

    def is_read_only(self, tool: str) -> bool:
        server = tool.split(".", 1)[0]
        return any(pattern in self._read_only for pattern in (tool, f"{server}.*", "*"))
