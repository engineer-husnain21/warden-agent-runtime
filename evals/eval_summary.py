from pydantic import BaseModel

from evals.scenario_result import ScenarioResult


class EvalSummary(BaseModel):
    """Suite-level scores (task success rate, mean tool-call accuracy) and average run usage."""

    scenarios: int
    passed: int
    success_rate: float
    tool_accuracy: float
    avg_tokens_per_run: float
    avg_llm_latency_seconds: float
    avg_cost_usd: float
    total_cost_usd: float

    @classmethod
    def from_results(cls, results: list[ScenarioResult]) -> "EvalSummary":
        count = len(results)
        if not count:
            return cls(
                scenarios=0,
                passed=0,
                success_rate=0.0,
                tool_accuracy=0.0,
                avg_tokens_per_run=0.0,
                avg_llm_latency_seconds=0.0,
                avg_cost_usd=0.0,
                total_cost_usd=0.0,
            )
        passed = sum(result.passed for result in results)
        tokens = sum(result.input_tokens + result.output_tokens for result in results)
        total_cost = sum(result.cost_usd for result in results)
        return cls(
            scenarios=count,
            passed=passed,
            success_rate=passed / count,
            tool_accuracy=sum(result.tool_accuracy for result in results) / count,
            avg_tokens_per_run=tokens / count,
            avg_llm_latency_seconds=sum(r.llm_latency_ms for r in results) / count / 1000,
            avg_cost_usd=total_cost / count,
            total_cost_usd=total_cost,
        )
