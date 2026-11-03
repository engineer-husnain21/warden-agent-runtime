"""Page chrome shared by every console page: page config, styles, header and status pills."""

from html import escape

import streamlit as st

BRAND = "Warden"
TAGLINE = "Governed AI agents"

# Run statuses and step statuses share one colour language.
STATUS_COLORS = {
    "pending": "#8A90A0",
    "running": "#4C8DFF",
    "awaiting_approval": "#F5A524",
    "completed": "#2EB67D",
    "succeeded": "#2EB67D",
    "failed": "#F04438",
    "denied": "#F04438",
    "skipped": "#8A90A0",
}
_DEFAULT_COLOR = "#8A90A0"

_STYLES = """
<style>
.warden-header { display: flex; align-items: baseline; gap: 0.75rem;
  padding: 0.25rem 0 0.75rem; margin-bottom: 0.5rem; border-bottom: 1px solid #262A33; }
.warden-header .brand { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
.warden-header .brand::before { content: ""; display: inline-block; width: 0.6rem; height: 0.6rem;
  margin-right: 0.5rem; border-radius: 0.15rem; background: #6E7BF2; }
.warden-header .tagline { color: #8A90A0; font-size: 0.9rem; }
.warden-pill { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; white-space: nowrap;
  color: var(--pill); background: color-mix(in srgb, var(--pill) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--pill) 40%, transparent); }
</style>
"""


def status_pill(status: str) -> str:
    """HTML for a coloured status pill; render with `st.markdown(..., unsafe_allow_html=True)`."""
    color = STATUS_COLORS.get(status, _DEFAULT_COLOR)
    label = escape(status.replace("_", " "))
    return f'<span class="warden-pill" style="--pill: {color}">{label}</span>'


def short_time(iso_timestamp: str) -> str:
    """'2026-11-02T09:00:05.123+00:00' -> '2026-11-02 09:00' (UTC)."""
    return iso_timestamp.replace("T", " ")[:16]


def setup_page(title: str) -> None:
    """Call first on every page: sets the tab title and draws the shared header."""
    st.set_page_config(page_title=f"{title} · {BRAND}", page_icon="🛡️", layout="wide")
    st.markdown(_STYLES, unsafe_allow_html=True)
    st.markdown(
        f'<div class="warden-header"><span class="brand">{BRAND}</span>'
        f'<span class="tagline">{TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )
