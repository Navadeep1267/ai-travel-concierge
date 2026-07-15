from __future__ import annotations

import uuid
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values

from agent.graph import build_travel_graph, run_travel_graph


st.set_page_config(
    page_title="Advanced AI Travel Agent",
    page_icon="🤖",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = dotenv_values(PROJECT_ROOT / ".env")


def get_setting(name: str) -> str:
    """Read configuration from Streamlit Cloud or local .env."""
    try:
        cloud_value = st.secrets.get(name, "")
    except Exception:
        cloud_value = ""

    if cloud_value:
        return str(cloud_value).strip()

    return str(LOCAL_CONFIG.get(name, "") or "").strip()


api_key = get_setting("GEMINI_API_KEY")
model_name = get_setting("GEMINI_MODEL")


st.title("🤖 Advanced AI Travel Agent")

st.write(
    "LangGraph travel agent with web search, live weather, "
    "country information, retries, state management and monitoring."
)

column1, column2, column3 = st.columns(3)

column1.metric(
    "Gemini API",
    "Loaded" if api_key else "Missing",
)

column2.metric(
    "Gemini model",
    model_name if model_name else "Missing",
)

column3.metric(
    "Available tools",
    "3",
)


if not api_key:
    st.error(
        "GEMINI_API_KEY is missing from .env "
        "or Streamlit Cloud secrets."
    )
    st.stop()

if not model_name:
    st.error(
        "GEMINI_MODEL is missing from .env "
        "or Streamlit Cloud secrets."
    )
    st.stop()


if "advanced_thread_id" not in st.session_state:
    st.session_state.advanced_thread_id = str(uuid.uuid4())

if "advanced_messages" not in st.session_state:
    st.session_state.advanced_messages = []

if "advanced_graph" not in st.session_state:
    try:
        st.session_state.advanced_graph = build_travel_graph(
            api_key=api_key,
            model_name=model_name,
        )
    except Exception as error:
        st.error("The LangGraph workflow could not be created.")
        st.code(f"{type(error).__name__}: {error}")
        st.stop()


with st.sidebar:
    st.header("Track B Features")

    st.write("✅ LangGraph workflow")
    st.write("✅ Web search")
    st.write("✅ Live weather")
    st.write("✅ Country information")
    st.write("✅ Automatic retries")
    st.write("✅ State management")
    st.write("✅ Performance monitoring")

    if st.button("Clear conversation"):
        st.session_state.advanced_messages = []
        st.session_state.advanced_thread_id = str(uuid.uuid4())
        st.rerun()


for message in st.session_state.advanced_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        tools = message.get("tools", [])

        if tools:
            with st.expander("Tools used"):
                for tool_name in tools:
                    st.write(f"• `{tool_name}`")


example_question = st.selectbox(
    "Example question",
    [
        "Choose an example",
        (
            "Plan a 3-day trip to Japan. Search for attractions, "
            "check the weather, provide country and currency "
            "information, and give packing advice."
        ),
        (
            "Check the current weather in Hyderabad and "
            "tell me what to pack."
        ),
        (
            "Search for the best tourist attractions in Jaipur "
            "and include source links."
        ),
    ],
)

if example_question != "Choose an example":
    st.info(f"Copy this question into the chat box:\n\n{example_question}")


question = st.chat_input("Ask the Advanced AI Travel Agent")


if question:
    st.session_state.advanced_messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "LangGraph is planning and calling travel tools..."
        ):
            try:
                result = run_travel_graph(
                    graph=st.session_state.advanced_graph,
                    user_query=question,
                    thread_id=st.session_state.advanced_thread_id,
                    message_history=st.session_state.advanced_messages,
                )

                answer = result.get(
                    "final_answer",
                    "No answer was generated.",
                )

                selected_tools = [
                    tool_call.get("name", "")
                    for tool_call in result.get("selected_tools", [])
                    if tool_call.get("name")
                ]

                st.markdown(answer)

                metric1, metric2, metric3 = st.columns(3)

                metric1.metric(
                    "Tools used",
                    len(selected_tools),
                )

                metric2.metric(
                    "Retries",
                    result.get("retry_count", 0),
                )

                metric3.metric(
                    "Response time",
                    f"{result.get('total_duration', 0):.2f}s",
                )

                with st.expander(
                    "View workflow details",
                    expanded=True,
                ):
                    st.write("### Selected tools")

                    for tool_name in selected_tools:
                        st.write(f"• `{tool_name}`")

                    st.write("### Tool results")

                    for tool_name, tool_result in result.get(
                        "tool_results",
                        {},
                    ).items():
                        st.write(f"#### {tool_name}")
                        st.code(tool_result)

                    errors = result.get("errors", [])

                    if errors:
                        st.write("### Handled errors")

                        for error in errors:
                            st.warning(error)

                st.session_state.advanced_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "tools": selected_tools,
                    }
                )

            except Exception as error:
                st.error(
                    "The Advanced Travel Agent could not complete "
                    "the request."
                )
                st.code(f"{type(error).__name__}: {error}")