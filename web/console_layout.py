"""Page chrome shared by every console page: page config, styles, header and status pills."""

from html import escape

import streamlit as st

from web.console_styles import build_styles
from web.icons import icon_svg
from web.theme import status_color

BRAND = "Warden"
TAGLINE = "Governed AI agents"


def status_pill(status: str) -> str:
    """HTML for a coloured status pill; render with `st.markdown(..., unsafe_allow_html=True)`."""
    label = escape(status.replace("_", " "))
    return f'<span class="warden-pill" style="--pill: {status_color(status)}">{label}</span>'


def metric_card(label: str, value: str, icon: str, color: str) -> str:
    """One coloured stat card (soft gradient, glowing border, coloured icon) as HTML."""
    return (
        f'<div class="w-metric" style="--c: {color}">'
        f'<div class="w-metric-icon">{icon_svg(icon)}</div>'
        f'<div><div class="w-metric-label">{escape(label)}</div>'
        f'<div class="w-metric-value">{escape(value)}</div></div></div>'
    )


def metric_row(cards: list[str]) -> str:
    """Lay metric cards out in a responsive row; render with unsafe_allow_html=True."""
    return f'<div class="w-metric-row">{"".join(cards)}</div>'


def short_time(iso_timestamp: str) -> str:
    """'2026-11-02T09:00:05.123+00:00' -> '2026-11-02 09:00' (UTC)."""
    return iso_timestamp.replace("T", " ")[:16]


def setup_page(title: str) -> None:
    """Call first on every page: sets the tab title and draws the shared header."""
    st.set_page_config(page_title=f"{title} · {BRAND}", page_icon="🛡️", layout="wide")
    st.markdown(build_styles(), unsafe_allow_html=True)
    st.markdown(
        f'<div class="warden-header"><span class="brand">{BRAND}</span>'
        f'<span class="tagline">{TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )
