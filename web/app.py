"""Warden console, home page: submit a task and see recent runs.

Run: `uv run streamlit run web/app.py` (the API must be running).
"""

from typing import Any

import streamlit as st

from web import theme
from web.console_layout import metric_card, metric_row, setup_page, short_time, status_pill
from web.console_state import SELECTED_RUN_KEY, get_api_client, render_sidebar
from web.warden_api_error import WardenApiError

AUTO_REFRESH_SECONDS = 5

setup_page("Agent runs")
render_sidebar()
api = get_api_client()

st.title("Agent runs")

with st.form("new_run", clear_on_submit=True):
    task = st.text_area(
        "New task",
        placeholder="Find orders that failed in the last 24 hours and open a GitHub issue "
        "for the top 3 causes",
    )
    if st.form_submit_button("Run"):
        try:
            run = api.create_run(task.strip())
            st.success(f"Run {run['id']} started. Open it on the Run detail page.")
        except WardenApiError as error:
            st.error(f"Could not start the run: {error.message}")

try:
    prefetched: list[dict[str, Any]] = [api.get_overview()]
except WardenApiError as error:
    st.error(f"Could not load runs: {error.message}")
    st.stop()

polling = bool(prefetched[0]["active"])


@st.fragment(run_every=AUTO_REFRESH_SECONDS if polling else None)
def overview_panel() -> None:
    """Stats and recent runs. Re-runs on its own every few seconds while a run is active."""
    # The full page run already fetched once; fragment re-runs fetch fresh data.
    overview = prefetched.pop() if prefetched else api.get_overview()
    if polling and not overview["active"]:
        st.rerun()  # nothing left to watch: a full rerun turns polling off

    colors = theme.HOME_METRIC_COLORS
    cards = [
        metric_card("Total runs", str(overview["total_runs"]), "play", colors["total_runs"]),
        metric_card(
            "Awaiting approval",
            str(overview["awaiting_approval"]),
            "shield",
            colors["awaiting_approval"],
        ),
        metric_card("Completed", str(overview["completed"]), "check", colors["completed"]),
        metric_card(
            "Total cost", f"${overview['total_cost_usd']:.5f}", "coins", colors["total_cost"]
        ),
    ]
    st.markdown(metric_row(cards), unsafe_allow_html=True)

    st.subheader("Recent runs")
    if overview["active"]:
        st.caption(f"Refreshing every {AUTO_REFRESH_SECONDS} s while runs are active.")
    if not overview["runs"]:
        st.info("No runs yet.")
    for run in overview["runs"]:
        with st.container(border=True):
            pill_col, task_col, meta_col, open_col = st.columns(
                [1.4, 6, 2.2, 1], vertical_alignment="center"
            )
            pill_col.markdown(status_pill(run["status"]), unsafe_allow_html=True)
            task_col.markdown(f"**{run['task']}**")
            meta_col.caption(
                f"{run['requested_by']} ({run['role']}) · {short_time(run['created_at'])}"
            )
            if open_col.button("Open", key=f"open-{run['id']}"):
                st.session_state[SELECTED_RUN_KEY] = run["id"]
                st.switch_page("pages/run_detail.py")


overview_panel()
