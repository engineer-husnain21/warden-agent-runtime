"""Warden console, home page: submit a task and see recent runs.

Run: `uv run streamlit run web/app.py` (the API must be running).
"""

import streamlit as st

from web.console_layout import setup_page
from web.console_state import get_api_client, render_sidebar
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

if runs:
    st.dataframe(
        [
            {
                "id": run["id"],
                "status": run["status"],
                "task": run["task"],
                "requested by": f"{run['requested_by']} ({run['role']})",
                "created": run["created_at"],
            }
            for run in runs
        ],
        hide_index=True,
        width="stretch",
        # Wide enough for "awaiting_approval" without cutting it off.
        column_config={"status": st.column_config.TextColumn("status", width="medium")},
    )
else:
    st.info("No runs yet.")
