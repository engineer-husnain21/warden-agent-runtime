"""Helpers for reading the console's HTML elements out of a Streamlit AppTest."""

import re

from streamlit.testing.v1 import AppTest

_CARD = re.compile(
    r'class="w-metric" style="--c: (#[0-9A-F]{6})">.*?'
    r'class="w-metric-label">([^<]*)</div><div class="w-metric-value">([^<]*)</div>'
)


def metric_cards(page: AppTest) -> dict[str, tuple[str, str]]:
    """label -> (value, colour) for every coloured metric card on the page."""
    html = " ".join(block.value for block in page.markdown)
    return {label: (value, color) for color, label, value in _CARD.findall(html)}
