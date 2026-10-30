from enum import StrEnum


class RunStepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    AWAITING_APPROVAL = "awaiting_approval"
    SKIPPED = "skipped"
