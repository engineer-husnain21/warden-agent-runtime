from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient

PAGE = Path(__file__).resolve().parents[3] / "web" / "pages" / "approvals.py"


def _page(fake: FakeWardenApiClient) -> AppTest:
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["api_client"] = fake
    return page.run()


def test_approvals_when_approve_clicked_calls_api() -> None:
    fake = FakeWardenApiClient()
    page = _page(fake)

    page.text_input(key="reason-a1").input("Looks right")
    page.button(key="approve-a1").click().run()

    assert fake.decisions == [("a1", True, "Looks right")]
    assert "Approved github.create_issue." in page.success[0].value


def test_approvals_when_reject_clicked_sends_rejection() -> None:
    fake = FakeWardenApiClient()
    page = _page(fake)

    page.button(key="reject-a1").click().run()

    assert fake.decisions == [("a1", False, "")]


def test_approvals_when_pending_shows_tool_and_arguments() -> None:
    page = _page(FakeWardenApiClient())

    assert not page.exception
    assert "github.create_issue" in page.markdown[0].value
    assert page.json[0].value is not None
