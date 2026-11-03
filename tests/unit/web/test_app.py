from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient
from web import theme

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


def test_app_when_loaded_shows_stats_row() -> None:
    app = _run(FakeWardenApiClient())

    stats = {metric.label: metric.value for metric in app.metric}
    assert stats == {
        "Total runs": "1",
        "Awaiting approval": "1",
        "Completed": "0",
        "Total cost": "$0.00157",
    }


def test_app_when_a_run_is_active_says_it_auto_refreshes() -> None:
    app = _run(FakeWardenApiClient())

    assert any("Refreshing every 5 s" in caption.value for caption in app.caption)
