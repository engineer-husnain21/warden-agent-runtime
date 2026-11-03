"""The console's one colour palette. Every coloured element (pills, cards, timeline, flow chart,
charts) reads its colours from here, so the console stays consistent."""

# Surfaces and text (match .streamlit/config.toml).
BACKGROUND = "#0B0C0F"
SURFACE = "#15171C"
BORDER = "#262A33"
TEXT = "#E6E8EE"
MUTED = "#8A90A0"

# Accent colours.
INDIGO = "#6E7BF2"
PURPLE = "#A855F7"
PINK = "#EC4899"
BLUE = "#3B82F6"
CYAN = "#06B6D4"
TEAL = "#14B8A6"
GREEN = "#22C55E"
AMBER = "#F59E0B"
RED = "#EF4444"

BRAND_GRADIENT = (INDIGO, PURPLE, PINK)

# Run and step statuses share one colour language.
STATUS_COLORS = {
    "pending": MUTED,
    "running": BLUE,
    "awaiting_approval": AMBER,
    "completed": GREEN,
    "succeeded": GREEN,
    "failed": RED,
    "denied": RED,
    "skipped": MUTED,
}

# One colour per kind of step, used by the timeline, the flow chart and the charts.
KIND_COLORS = {
    "plan": PURPLE,
    "tool_selection": BLUE,
    "permission_check": CYAN,
    "approval": AMBER,
    "tool_call": PINK,
    "review": TEAL,
    "report": GREEN,
}

RUN_METRIC_COLORS = {"llm_calls": BLUE, "tokens": PURPLE, "latency": AMBER, "cost": GREEN}
HOME_METRIC_COLORS = {
    "total_runs": INDIGO,
    "awaiting_approval": AMBER,
    "completed": GREEN,
    "total_cost": TEAL,
}


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status, MUTED)


def kind_color(kind: str) -> str:
    return KIND_COLORS.get(kind, MUTED)
