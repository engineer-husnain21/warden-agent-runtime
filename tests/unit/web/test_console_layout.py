from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient
from web import theme
from web.console_layout import metric_card, metric_row, run_row_key, short_time, status_pill

WEB = Path(__file__).resolve().parents[3] / "web"
PAGES = [WEB / "app.py", WEB / "pages" / "run_detail.py", WEB / "pages" / "approvals.py"]


@pytest.mark.parametrize("page_path", PAGES, ids=lambda path: path.stem)
def test_every_page_when_rendered_shows_warden_header(page_path: Path) -> None:
    page = AppTest.from_file(page_path, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()

    page.run()

    assert not page.exception
    header = next(b.value for b in page.markdown if 'class="warden-header"' in b.value)
    assert ">Warden<" in header
    assert "Governed AI agents" in header


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("pending", theme.MUTED),
        ("running", theme.BLUE),
        ("awaiting_approval", theme.AMBER),
        ("completed", theme.GREEN),
        ("failed", theme.RED),
    ],
)
def test_status_pill_when_run_status_uses_its_colour(status: str, color: str) -> None:
    pill = status_pill(status)

    assert f"--pill: {color}" in pill
    assert status.replace("_", " ") in pill


def test_status_pill_when_status_unknown_falls_back_to_grey_and_escapes() -> None:
    pill = status_pill("<weird>")

    assert f"--pill: {theme.MUTED}" in pill
    assert "&lt;weird&gt;" in pill


def test_run_row_key_when_built_matches_the_styled_class_prefix() -> None:
    assert run_row_key("r1") == "run-row-r1"


def test_short_time_when_iso_timestamp_shows_minutes() -> None:
    assert short_time("2026-11-02T09:00:05.123+00:00") == "2026-11-02 09:00"


def test_metric_card_when_built_has_colour_icon_and_escaped_text() -> None:
    card = metric_card("Cost <x>", "$1", "dollar", theme.GREEN)

    assert f"--c: {theme.GREEN}" in card
    assert "<svg" in card
    assert "Cost &lt;x&gt;" in card
    assert metric_row([card, card]).count('class="w-metric"') == 2
