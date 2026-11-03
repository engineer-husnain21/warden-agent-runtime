from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fakes.fake_warden_api_client import FakeWardenApiClient

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
