from pydantic import BaseModel, Field

from app.schemas.agents.step_record import StepRecord


class ReporterInput(BaseModel):
    task: str = Field(min_length=1)
    steps: list[StepRecord]
