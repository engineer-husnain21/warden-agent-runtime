from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.role import Role
from evals.scenario_expectation import ScenarioExpectation

ApprovalAction = Literal["approve", "reject", "none"]


class Scenario(BaseModel):
    """One eval case: a task, who asks for it, how a human answers approvals, and what to expect.

    `approval: none` means the run must not pause; if it does, the runner rejects the request
    and the scenario fails.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str
    task: str = Field(min_length=3)
    role: Role = Role.OPERATOR
    approval: ApprovalAction = "none"
    # e.g. "smoke": the subset CI runs on every PR (`--tag smoke`); see docs/adr/0004.
    tags: list[str] = []
    expect: ScenarioExpectation
