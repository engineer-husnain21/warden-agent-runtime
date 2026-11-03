"""Warden console, home page: submit a task and see recent runs.

Run: `uv run streamlit run web/app.py` (the API must be running).
"""

import streamlit as st

from web.console_layout import setup_page, short_time, status_pill
from web.console_state import SELECTED_RUN_KEY, get_api_client, render_sidebar
from web.warden_api_error import WardenApiError

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

st.subheader("Recent runs")
st.button("Refresh")
try:
    runs = api.list_runs()
except WardenApiError as error:
    st.error(f"Could not load runs: {error.message}")
    runs = []

if not runs:
    st.info("No runs yet.")

for run in runs:
    with st.container(border=True):
        pill_col, task_col, meta_col, open_col = st.columns(
            [1.4, 6, 2.2, 1], vertical_alignment="center"
        )
        pill_col.markdown(status_pill(run["status"]), unsafe_allow_html=True)
        task_col.markdown(f"**{run['task']}**")
        meta_col.caption(f"{run['requested_by']} ({run['role']}) · {short_time(run['created_at'])}")
        if open_col.button("Open", key=f"open-{run['id']}"):
            st.session_state[SELECTED_RUN_KEY] = run["id"]
            st.switch_page("pages/run_detail.py")
