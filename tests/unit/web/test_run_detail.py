from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient

PAGE = Path(__file__).resolve().parents[3] / "web" / "pages" / "run_detail.py"


def test_run_detail_when_loaded_shows_steps_table() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()

    page.run()

    assert not page.exception
    assert len(page.dataframe) == 1
    assert [metric.value for metric in page.metric] == ["6", "6,150", "6.2 s", "$0.00157"]
    assert any("All good." in block.value for block in page.markdown)


def test_run_detail_when_api_down_shows_error() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient(fail_with="API not reachable")

    page.run()

    assert "Could not load runs" in page.error[0].value
