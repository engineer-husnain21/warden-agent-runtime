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


def test_run_detail_when_loaded_shows_bordered_metric_cards_with_icons() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()

    page.run()

    assert [m.label for m in page.metric] == ["LLM calls", "Tokens", "LLM latency", "Est. cost"]
    assert all(m.proto.icon.startswith(":material/") for m in page.metric)
    assert all(m.proto.show_border for m in page.metric)


def test_run_detail_when_loaded_draws_run_flow_chart() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()

    page.run()

    [chart] = page.get("graphviz_chart")
    assert "digraph run" in chart.proto.spec
    assert "start -> s0;" in chart.proto.spec


def test_run_detail_when_opened_from_home_preselects_that_run() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()
    page.session_state["selected_run_id"] = "r1"

    page.run()

    assert page.selectbox[0].value == "r1"


def test_run_detail_when_api_down_shows_error() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient(fail_with="API not reachable")

    page.run()

    assert "Could not load runs" in page.error[0].value


def test_run_detail_when_cell_empty_shows_dash_not_none() -> None:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = FakeWardenApiClient()

    page.run()

    table = page.dataframe[0].value
    assert table["tool"].tolist() == ["—"]
    assert "None" not in table.astype(str).to_string()
