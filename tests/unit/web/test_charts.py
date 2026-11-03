from typing import Any

from web import theme
from web.charts import status_donut_chart, step_usage_charts


def _step(position: int, kind: str, tokens: int, cost: float) -> dict[str, Any]:
    return {
        "position": position,
        "kind": kind,
        "input_tokens": tokens,
        "output_tokens": 0,
        "cost_usd": cost,
    }


def test_step_usage_charts_when_llm_steps_given_bars_use_kind_palette() -> None:
    steps = [_step(0, "plan", 900, 0.0003), _step(1, "tool_call", 0, 0.0)]

    charts = step_usage_charts(steps)

    assert charts is not None
    tokens_spec, cost_spec = (chart.to_dict() for chart in charts)
    assert tokens_spec["title"] == "Tokens per step"
    assert cost_spec["title"] == "Cost per step"
    scale = tokens_spec["encoding"]["color"]["scale"]
    assert dict(zip(scale["domain"], scale["range"], strict=True)) == theme.KIND_COLORS
    # Steps without LLM usage (tool calls) are left out.
    [rows] = tokens_spec["datasets"].values()  # Altair moves inline data into `datasets`
    assert [row["step"] for row in rows] == ["#0 Plan"]


def test_step_usage_charts_when_no_llm_steps_returns_none() -> None:
    assert step_usage_charts([_step(0, "tool_call", 0, 0.0)]) is None


def test_status_donut_chart_when_runs_exist_colours_each_status() -> None:
    chart = status_donut_chart({"completed": 3, "awaiting_approval": 1, "failed": 0})

    assert chart is not None
    spec = chart.to_dict()
    assert spec["mark"]["type"] == "arc"
    assert spec["mark"]["innerRadius"] > 0
    scale = spec["encoding"]["color"]["scale"]
    assert dict(zip(scale["domain"], scale["range"], strict=True)) == {
        "awaiting_approval": theme.AMBER,
        "completed": theme.GREEN,
        "failed": theme.RED,
    }
    [rows] = spec["datasets"].values()
    assert {row["status"] for row in rows} == {"completed", "awaiting_approval"}


def test_status_donut_chart_when_no_runs_returns_none() -> None:
    assert status_donut_chart({}) is None
