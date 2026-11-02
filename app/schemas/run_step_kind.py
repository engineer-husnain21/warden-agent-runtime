from enum import StrEnum


class RunStepKind(StrEnum):
    PLAN = "plan"
    TOOL_SELECTION = "tool_selection"
    PERMISSION_CHECK = "permission_check"
    APPROVAL = "approval"
    TOOL_CALL = "tool_call"
    REVIEW = "review"
    REPORT = "report"
