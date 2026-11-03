"""Approvals inbox: risky tool calls waiting for a human. Admins approve or reject them here."""

import streamlit as st

from web.console_layout import NEEDS_APPROVAL_BADGE, approval_card_key, setup_page, short_time
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
    pending = api.list_pending_approvals_with_context()
except WardenApiError as error:
    st.error(f"Could not load approvals: {error.message}")
    st.stop()

if not pending:
    st.info("Nothing is waiting for approval.")
    st.button("Refresh")
    st.stop()

for approval in pending:
    with st.container(border=True, key=approval_card_key(approval["id"])):
        title_col, badge_col = st.columns([5, 1.4], vertical_alignment="center")
        title_col.markdown(f"#### `{approval['tool_name']}`")
        badge_col.markdown(NEEDS_APPROVAL_BADGE, unsafe_allow_html=True)

        info_col, args_col = st.columns([1, 1])
        with info_col:
            st.markdown(
                f"**Requested by** {approval['requested_by']} ({approval['requested_role']})  \n"
                f"**Run** {approval['run_task']}  \n"
                f"**Step** {approval['step_position'] + 1} · {short_time(approval['created_at'])}"
            )
            st.info(approval["policy_reason"], icon=":material/policy:")
        with args_col:
            st.caption("Arguments")
            st.json(approval["tool_arguments"])

        reason = st.text_input("Reason (optional)", key=f"reason-{approval['id']}")
        approve_col, reject_col = st.columns(2)
        decision: bool | None = None
        if approve_col.button(
            "Approve",
            key=f"approve-{approval['id']}",
            type="primary",
            icon=":material/check:",
            width="stretch",
        ):
            decision = True
        if reject_col.button(
            "Reject", key=f"reject-{approval['id']}", icon=":material/close:", width="stretch"
        ):
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
