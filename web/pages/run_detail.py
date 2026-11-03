"""Run detail: status, final report, tokens / latency / cost, and the full step trace."""

import streamlit as st

from web.console_layout import setup_page, short_time, status_pill
from web.console_state import SELECTED_RUN_KEY, get_api_client, render_sidebar
from web.run_flow import build_run_flow_dot
from web.trace_format import expander_title, timeline_html, trace_row
from web.warden_api_error import WardenApiError

setup_page("Run detail")
render_sidebar()
api = get_api_client()

st.title("Run detail")

try:
    runs = api.list_runs()
except WardenApiError as error:
    st.error(f"Could not load runs: {error.message}")
    st.stop()

if not runs:
    st.info("No runs yet. Start one on the home page.")
    st.stop()

labels = {run["id"]: f"{run['task'][:70]}  ({run['id'][:8]})" for run in runs}
options = list(labels)
selected = st.session_state.get(SELECTED_RUN_KEY)
run_id = st.selectbox(
    "Run",
    options=options,
    index=options.index(selected) if selected in options else 0,
    format_func=lambda key: labels[key],
)
st.button("Refresh")

run = api.get_run(run_id)
metrics = api.get_metrics(run_id)
report = api.get_report(run_id)
steps = api.get_steps(run_id)

st.markdown(
    f"{status_pill(run['status'])}&nbsp; requested by {run['requested_by']} ({run['role']})"
    f" · {short_time(run['created_at'])}",
    unsafe_allow_html=True,
)
if run.get("error"):
    st.error(run["error"])

tokens = metrics["total_input_tokens"] + metrics["total_output_tokens"]
cards = st.columns(4)
cards[0].metric("LLM calls", metrics["llm_calls"], icon=":material/smart_toy:", border=True)
cards[1].metric("Tokens", f"{tokens:,}", icon=":material/token:", border=True)
cards[2].metric(
    "LLM latency",
    f"{metrics['total_latency_ms'] / 1000:.1f} s",
    icon=":material/timer:",
    border=True,
)
cards[3].metric(
    "Est. cost", f"${metrics['total_cost_usd']:.5f}", icon=":material/payments:", border=True
)

st.subheader("Run flow")
st.graphviz_chart(build_run_flow_dot(steps, run["status"]), width="stretch")

st.subheader("Report")
if report.get("report"):
    st.markdown(report["report"])
else:
    st.info("No report yet: the run is still going or waiting for approval.")

st.subheader("Trace")
st.markdown(timeline_html(steps), unsafe_allow_html=True)

with st.expander("Table view", icon=":material/table_rows:"):
    st.dataframe(
        [trace_row(step) for step in steps],
        hide_index=True,
        width="stretch",
        # Wide enough for "awaiting_approval" / "needs_approval" without cutting them off.
        column_config={
            "status": st.column_config.TextColumn("status", width="medium"),
            "decision": st.column_config.TextColumn("decision", width="medium"),
        },
    )

st.caption("Step details")
for step in steps:
    if step["tool_arguments"] or step["output"]:
        with st.expander(expander_title(step)):
            st.json({"arguments": step["tool_arguments"], "output": step["output"]})
