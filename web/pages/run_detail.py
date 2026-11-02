"""Run detail: status, final report, tokens / latency / cost, and the full step trace."""

import streamlit as st

from web.console_state import get_api_client, render_sidebar
from web.trace_format import decision_label
from web.warden_api_error import WardenApiError

st.set_page_config(page_title="Run detail · Warden", layout="wide")
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

labels = {run["id"]: f"{run['status']:<18} {run['task'][:70]}  ({run['id'][:8]})" for run in runs}
run_id = st.selectbox("Run", options=list(labels), format_func=lambda key: labels[key])
st.button("Refresh")

run = api.get_run(run_id)
metrics = api.get_metrics(run_id)
report = api.get_report(run_id)
steps = api.get_steps(run_id)

st.caption(f"Requested by {run['requested_by']} ({run['role']}) · status **{run['status']}**")
if run.get("error"):
    st.error(run["error"])

columns = st.columns(4)
columns[0].metric("LLM calls", metrics["llm_calls"])
columns[1].metric("Tokens", f"{metrics['total_input_tokens'] + metrics['total_output_tokens']:,}")
columns[2].metric("LLM latency", f"{metrics['total_latency_ms'] / 1000:.1f} s")
columns[3].metric("Est. cost", f"${metrics['total_cost_usd']:.5f}")

st.subheader("Report")
if report.get("report"):
    st.markdown(report["report"])
else:
    st.info("No report yet: the run is still going or waiting for approval.")

st.subheader("Trace")
st.dataframe(
    [
        {
            "#": step["position"],
            "kind": step["kind"],
            "status": step["status"],
            "agent": step["agent"],
            "tool": step["tool_name"],
            "decision": decision_label(step),
            "tokens": step["input_tokens"] + step["output_tokens"],
            "latency ms": round(step["latency_ms"]),
            "cost $": round(step["cost_usd"], 6),
        }
        for step in steps
    ],
    hide_index=True,
    width="stretch",
    # Wide enough for "awaiting_approval" / "needs_approval" without cutting them off.
    column_config={
        "status": st.column_config.TextColumn("status", width="medium"),
        "decision": st.column_config.TextColumn("decision", width="medium"),
    },
)
for step in steps:
    if step["tool_arguments"] or step["output"]:
        with st.expander(f"#{step['position']} {step['kind']} · {step['tool_name'] or ''}"):
            st.json({"arguments": step["tool_arguments"], "output": step["output"]})
