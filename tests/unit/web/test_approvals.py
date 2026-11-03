from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient
from web.console_layout import approval_card_key

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
    assert any("github.create_issue" in block.value for block in page.markdown)
    assert page.json[0].value is not None


def test_approvals_when_pending_shows_card_with_requester_role_and_policy_reason() -> None:
    page = _page(FakeWardenApiClient())

    text = " ".join(block.value for block in page.markdown)
    assert "oscar (operator)" in text
    assert "Find failed orders" in text
    assert "only after a human approves it" in page.info[0].value
    approve = page.button(key="approve-a1")
    assert approve.proto.type == "primary"


def test_approvals_when_pending_shows_pulsing_badge_in_keyed_card() -> None:
    page = _page(FakeWardenApiClient())

    assert any(
        "w-badge-pulse" in block.value and "Needs approval" in block.value
        for block in page.markdown
    )
    styles = next(block.value for block in page.markdown if "@keyframes w-pulse" in block.value)
    assert 'div[class*="st-key-approval-"]' in styles
    assert approval_card_key("a1") == "approval-a1"
