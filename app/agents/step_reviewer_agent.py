import json

from app.agents.base_agent import BaseAgent
from app.agents.tool_result_text import format_tool_result
from app.schemas.agents.step_reviewer_input import StepReviewerInput
from app.schemas.agents.step_reviewer_output import StepReviewerOutput


class StepReviewerAgent(BaseAgent[StepReviewerInput, StepReviewerOutput]):
    """Judges whether one step's tool result is good enough to move on."""

    name = "step_reviewer"

    async def run(self, input: StepReviewerInput) -> StepReviewerOutput:
        if not input.result.ok:
            # A failed call is never good enough; no need to spend an LLM call on it.
            return StepReviewerOutput(
                ok=False, feedback=f"The tool call failed: {input.result.error}"
            )

        messages = await self._build_messages(
            "step_reviewer",
            task=input.task,
            step=input.step.description,
            tool=input.call.tool,
            arguments=json.dumps(input.call.arguments, ensure_ascii=False),
            result=format_tool_result(input.result),
        )
        review, usage = await self._complete_json(messages, StepReviewerOutput)
        return review.model_copy(update={"usage": usage})
