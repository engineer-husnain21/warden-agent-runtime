"""Altair charts for the console, coloured with the palette in web/theme.py."""

from typing import Any

import altair as alt

from web import theme
from web.trace_format import KIND_TITLES

_ROW_HEIGHT = 26
_AXIS_HEIGHT = 40


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
    # Horizontal bars: one row per step, so every step label fits without being thinned out.
    base = alt.Chart(alt.InlineData(values=rows)).mark_bar(cornerRadiusEnd=4)
    color = alt.Color(
        "kind:N",
        scale=alt.Scale(domain=list(theme.KIND_COLORS), range=list(theme.KIND_COLORS.values())),
        legend=None,
    )
    y = alt.Y("step:N", sort=None, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=0))
    height = _ROW_HEIGHT * len(rows) + _AXIS_HEIGHT
    tokens = base.encode(
        y=y,
        x=alt.X("tokens:Q", title="Tokens"),
        color=color,
        tooltip=["step:N", alt.Tooltip("tokens:Q", format=",")],
    ).properties(title="Tokens per step", height=height)
    cost = base.encode(
        y=y,
        x=alt.X("cost_usd:Q", title="USD", axis=alt.Axis(format="$.4f", tickCount=4)),
        color=color,
        tooltip=["step:N", alt.Tooltip("cost_usd:Q", format="$.6f")],
    ).properties(title="Cost per step", height=height)
    return tokens, cost


def status_donut_chart(status_counts: dict[str, int]) -> alt.Chart | None:
    """Donut of runs per status, in the status colours. None when there are no runs."""
    rows = [{"status": status, "runs": count} for status, count in status_counts.items() if count]
    if not rows:
        return None
    statuses = [status for status in theme.STATUS_COLORS if status in status_counts]
    statuses += [status for status in status_counts if status not in statuses]
    chart: alt.Chart = (
        alt.Chart(alt.InlineData(values=rows))
        .mark_arc(innerRadius=55, outerRadius=95, cornerRadius=4, padAngle=0.02)
        .encode(
            theta=alt.Theta("runs:Q"),
            color=alt.Color(
                "status:N",
                scale=alt.Scale(domain=statuses, range=[theme.status_color(s) for s in statuses]),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=["status:N", "runs:Q"],
        )
        .properties(title="Runs by status", height=260)
    )
    return chart
