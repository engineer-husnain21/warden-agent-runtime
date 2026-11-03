"""Altair charts for the console, coloured with the palette in web/theme.py."""

from typing import Any

import altair as alt

from web import theme
from web.trace_format import KIND_TITLES

_HEIGHT = 230


def step_usage_charts(steps: list[dict[str, Any]]) -> tuple[alt.Chart, alt.Chart] | None:
    """Bar charts of tokens and cost per LLM step, bars coloured by step kind.
    None when no step used the LLM yet."""
    rows = [
        {
            "step": f"#{step['position']} {KIND_TITLES.get(step['kind'], step['kind'])}",
            "kind": step["kind"],
            "tokens": step["input_tokens"] + step["output_tokens"],
            "cost_usd": step["cost_usd"],
        }
        for step in steps
        if step["input_tokens"] + step["output_tokens"] > 0
    ]
    if not rows:
        return None
    base = alt.Chart(alt.InlineData(values=rows)).mark_bar(
        cornerRadiusTopLeft=5, cornerRadiusTopRight=5
    )
    color = alt.Color(
        "kind:N",
        scale=alt.Scale(domain=list(theme.KIND_COLORS), range=list(theme.KIND_COLORS.values())),
        legend=None,
    )
    x = alt.X("step:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30))
    tokens = base.encode(
        x=x,
        y=alt.Y("tokens:Q", title="Tokens"),
        color=color,
        tooltip=["step:N", alt.Tooltip("tokens:Q", format=",")],
    ).properties(title="Tokens per step", height=_HEIGHT)
    cost = base.encode(
        x=x,
        y=alt.Y("cost_usd:Q", title="USD", axis=alt.Axis(format="$.5f")),
        color=color,
        tooltip=["step:N", alt.Tooltip("cost_usd:Q", format="$.6f")],
    ).properties(title="Cost per step", height=_HEIGHT)
    return tokens, cost
