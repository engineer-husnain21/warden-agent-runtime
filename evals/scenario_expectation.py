from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioExpectation(BaseModel):
    """What a correct run of a scenario looks like. Tool names are `<server>.<tool>`."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"] = "completed"
    # Tools the agent should pick (tool-call accuracy compares these with what it picked).
    tools: list[str] = Field(min_length=1)
    # Extra tools that do not count against accuracy, e.g. looking at the schema first.
    allowed_extra_tools: list[str] = ["warehouse.list_tables", "warehouse.describe_table"]
    # Tools that must have run successfully / must never have run.
    executed: list[str] = []
    not_executed: list[str] = []
    # Tools the permission policy must have denied.
    denied: list[str] = []
    # Case-insensitive substrings the final report must / must not contain.
    report_contains: list[str] = []
    report_excludes: list[str] = []
