"""Approvals inbox: risky tool calls waiting for a human. Admins approve or reject them here."""

import streamlit as st

from web.console_layout import setup_page
from web.console_state import get_api_client, render_sidebar
from web.warden_api_error import WardenApiError

setup_page("Approvals")
render_sidebar()
api = get_api_client()

st.title("Approvals")
st.caption("Only admin API keys can decide. The paused run resumes as soon as you decide.")

if flash := st.session_state.pop("approval_flash", None):
    st.success(flash)

try:
    pending = api.list_pending_approvals()
except WardenApiError as error:
    st.error(f"Could not load approvals: {error.message}")
    st.stop()

if not pending:
    st.info("Nothing is waiting for approval.")
    st.button("Refresh")
    st.stop()

for approval in pending:
    with st.container(border=True):
        st.markdown(
            f"**{approval['tool_name']}** · requested by {approval['requested_by']} · "
            f"run `{approval['run_id'][:8]}` step {approval['step_position'] + 1}"
        )
        st.json(approval["tool_arguments"])
        reason = st.text_input("Reason (optional)", key=f"reason-{approval['id']}")
        approve, reject = st.columns(2)
        decision: bool | None = None
        if approve.button("Approve", key=f"approve-{approval['id']}", type="primary"):
            decision = True
        if reject.button("Reject", key=f"reject-{approval['id']}"):
            decision = False
        if decision is not None:
            try:
                api.decide(approval["id"], decision, reason)
            except WardenApiError as error:
                st.error(f"Could not record the decision: {error.message}")
            else:
                verb = "Approved" if decision else "Rejected"
                st.session_state["approval_flash"] = f"{verb} {approval['tool_name']}."
                st.rerun()
