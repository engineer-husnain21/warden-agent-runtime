from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient

APP = Path(__file__).resolve().parents[3] / "web" / "app.py"


def _run(fake: FakeWardenApiClient) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["api_client"] = fake
    return app.run()


def test_app_when_runs_exist_shows_runs_table() -> None:
    app = _run(FakeWardenApiClient())

    assert not app.exception
    assert app.title[0].value == "Agent runs"
    assert len(app.dataframe) == 1


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
