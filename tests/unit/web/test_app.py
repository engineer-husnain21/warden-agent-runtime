from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient
from tests.unit.web.page_helpers import metric_cards
from web import theme
from web.console_layout import run_row_key

APP = Path(__file__).resolve().parents[3] / "web" / "app.py"


def _run(fake: FakeWardenApiClient) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["api_client"] = fake
    return app.run()


def test_app_when_runs_exist_shows_a_row_with_status_pill() -> None:
    app = _run(FakeWardenApiClient())

    assert not app.exception
    assert app.title[0].value == "Agent runs"
    pills = [b.value for b in app.markdown if 'class="warden-pill"' in b.value]
    assert len(pills) == 1
    assert "awaiting approval" in pills[0]
    assert theme.AMBER in pills[0]
    assert app.button(key="open-r1") is not None


def _block_ids(node: Any) -> list[str]:
    proto: Any = getattr(node, "proto", None)
    ids = [proto.id] if type(proto).__name__ == "Block" and proto.id else []
    for child in getattr(node, "children", {}).values():
        ids += _block_ids(child)
    return ids


def test_app_when_runs_exist_renders_each_row_in_a_styled_keyed_container() -> None:
    app = _run(FakeWardenApiClient())

    # The `st-key-run-row-*` class carries the fixed pill / wrapping task / Open button widths.
    assert any(block_id.endswith(run_row_key("r1")) for block_id in _block_ids(app._tree))
    styles = next(b.value for b in app.markdown if "<style>" in b.value)
    assert 'div[class*="st-key-run-row-"] > :first-child' in styles
    assert "white-space: nowrap" in styles


def test_app_when_task_submitted_creates_run() -> None:
    fake = FakeWardenApiClient()
    app = _run(fake)

    app.text_area[0].input("Count failed orders")
    app.button[0].click().run()

    assert fake.created == ["Count failed orders"]
    assert "Run r2 started" in app.success[0].value


def test_app_when_api_down_shows_error() -> None:
    app = _run(FakeWardenApiClient(fail_with="API not reachable"))

    assert "Could not load runs" in app.error[0].value


def test_app_when_loaded_shows_coloured_stats_row() -> None:
    app = _run(FakeWardenApiClient())

    assert metric_cards(app) == {
        "Total runs": ("1", theme.INDIGO),
        "Awaiting approval": ("1", theme.AMBER),
        "Completed": ("0", theme.GREEN),
        "Total cost": ("$0.00157", theme.TEAL),
    }


def test_app_when_a_run_is_active_says_it_auto_refreshes() -> None:
    app = _run(FakeWardenApiClient())

    assert any("Refreshing every 5 s" in caption.value for caption in app.caption)


def test_app_when_runs_exist_shows_status_donut() -> None:
    app = _run(FakeWardenApiClient())

    [donut] = app.get("vega_lite_chart")
    assert '"arc"' in donut.proto.spec
    # The title is a Streamlit subheader, not a Vega title that can be clipped at the top.
    assert [header.value for header in app.subheader] == ["Recent runs", "Runs by status"]
