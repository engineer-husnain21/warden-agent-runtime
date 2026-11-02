import operator
from typing import Annotated, Any, TypedDict


class RunState(TypedDict, total=False):
    """LangGraph state of one run. Plain JSON values only, so checkpoints stay portable.

    Pydantic models (PlanStep, ToolCall, ToolResult, StepRecord, ...) are stored as dicts.
    `records` and `previous_results` are append-only: nodes return new items, LangGraph adds them.
    """

    run_id: str
    task: str
    role: str
    tools: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    current: int
    attempt: int
    feedback: str | None
    pending_call: dict[str, Any] | None
    policy_decision: str | None
    approval: dict[str, Any] | None
    last_result: dict[str, Any] | None
    records: Annotated[list[dict[str, Any]], operator.add]
    previous_results: Annotated[list[str], operator.add]
    report: str | None
