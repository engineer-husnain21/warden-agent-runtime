from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient
from web.console_layout import short_time, status_pill

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
        ("pending", "#8A90A0"),
        ("running", "#4C8DFF"),
        ("awaiting_approval", "#F5A524"),
        ("completed", "#2EB67D"),
        ("failed", "#F04438"),
    ],
)
def test_status_pill_when_run_status_uses_its_colour(status: str, color: str) -> None:
    pill = status_pill(status)

    assert f"--pill: {color}" in pill
    assert status.replace("_", " ") in pill


def test_status_pill_when_status_unknown_falls_back_to_grey_and_escapes() -> None:
    pill = status_pill("<weird>")

    assert "--pill: #8A90A0" in pill
    assert "&lt;weird&gt;" in pill


def test_short_time_when_iso_timestamp_shows_minutes() -> None:
    assert short_time("2026-11-02T09:00:05.123+00:00") == "2026-11-02 09:00"
