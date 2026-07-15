from __future__ import annotations

from collections import Counter
from statistics import mean

import streamlit as st

from monitoring.logger import read_events


st.set_page_config(
    page_title="Agent Monitoring",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Agent Monitoring Dashboard")

st.write(
    "This dashboard shows agent requests, tool usage, "
    "response time, retries and errors."
)


try:
    events = read_events(limit=2000)
except Exception as error:
    st.error("Monitoring events could not be loaded.")
    st.code(f"{type(error).__name__}: {error}")
    events = []


st.caption(f"Monitoring events found: {len(events)}")


agent_events = [
    event
    for event in events
    if event.get("event") == "agent_completed"
]

tool_events = [
    event
    for event in events
    if event.get("event") == "tool_call"
]

retry_events = [
    event
    for event in events
    if event.get("event") == "agent_retry"
]

error_events = [
    event
    for event in events
    if (
        event.get("success") is False
        or "error" in str(event.get("event", "")).lower()
        or "quota" in str(event.get("event", "")).lower()
    )
]


total_requests = len(agent_events)

successful_requests = sum(
    1
    for event in agent_events
    if event.get("success") is True
)

failed_requests = sum(
    1
    for event in agent_events
    if event.get("success") is False
)

success_rate = (
    successful_requests / total_requests * 100
    if total_requests
    else 0.0
)

durations = []

for event in agent_events:
    try:
        durations.append(
            float(event.get("duration_seconds", 0))
        )
    except (TypeError, ValueError):
        continue

average_response_time = (
    mean(durations)
    if durations
    else 0.0
)


tool_counter = Counter(
    str(event.get("tool", "unknown"))
    for event in tool_events
)


row1_col1, row1_col2, row1_col3 = st.columns(3)

row1_col1.metric(
    "Total requests",
    total_requests,
)

row1_col2.metric(
    "Successful requests",
    successful_requests,
)

row1_col3.metric(
    "Failed requests",
    failed_requests,
)


row2_col1, row2_col2, row2_col3 = st.columns(3)

row2_col1.metric(
    "Success rate",
    f"{success_rate:.1f}%",
)

row2_col2.metric(
    "Average response time",
    f"{average_response_time:.2f} seconds",
)

row2_col3.metric(
    "Total retries",
    len(retry_events),
)


st.divider()

st.subheader("🛠️ Tool Usage")

tool_rows = [
    {
        "Tool": tool_name,
        "Calls": count,
    }
    for tool_name, count in tool_counter.items()
]

if tool_rows:
    st.dataframe(
        tool_rows,
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(
        {
            row["Tool"]: row["Calls"]
            for row in tool_rows
        }
    )
else:
    st.info(
        "No tool calls are recorded yet. "
        "Run a request from the Travel Agent page first."
    )


st.divider()

st.subheader("⚠️ Recent Errors")

if error_events:
    recent_errors = error_events[-20:]

    error_rows = []

    for event in recent_errors:
        error_rows.append(
            {
                "Timestamp": event.get("timestamp", ""),
                "Event": event.get("event", ""),
                "Tool": event.get("tool", ""),
                "Error type": event.get("error_type", ""),
                "Success": event.get("success", ""),
            }
        )

    st.dataframe(
        error_rows,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("No errors have been recorded.")


st.divider()

with st.expander("View recent monitoring events"):
    if events:
        st.dataframe(
            events[-100:],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No monitoring data is available yet. "
            "Open Travel Agent and submit one request."
        )


if st.button("Refresh monitoring data"):
    st.rerun()