from pathlib import Path

import streamlit as st
from dotenv import dotenv_values


st.set_page_config(
    page_title="AI Travel Agent",
    page_icon="🤖",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

local_config = dotenv_values(ENV_FILE)


def get_setting(name: str) -> str:
    """Read Streamlit Cloud secrets, then the local .env file."""
    try:
        cloud_value = st.secrets.get(name, "")
    except Exception:
        cloud_value = ""

    if cloud_value:
        return str(cloud_value).strip()

    return str(local_config.get(name, "") or "").strip()


api_key = get_setting("GEMINI_API_KEY")
model_name = get_setting("GEMINI_MODEL")
st.caption(f"Configuration file: {ENV_FILE}")
st.caption(f"File exists: {ENV_FILE.exists()}")
st.caption(f"API key loaded: {'Yes' if api_key else 'No'}")
st.caption(f"Model loaded: {model_name or 'No'}")


st.title("🤖 AI Travel Agent")
st.write(
    "Ask about destinations, attractions, weather, packing, "
    "and travel planning."
)

col1, col2 = st.columns(2)

col1.metric(
    "Gemini API key",
    "Loaded" if api_key else "Missing",
)

col2.metric(
    "Gemini model",
    model_name if model_name else "Missing",
)


if not api_key:
    st.error(
        "GEMINI_API_KEY is missing. Add it to the .env file."
    )
    st.stop()

if not model_name:
    st.error(
        "GEMINI_MODEL is missing. Add it to the .env file."
    )
    st.stop()


try:
    from agent.travel_agent import run_travel_agent

except Exception as error:
    st.error("Unable to import the Travel Agent module.")
    st.code(f"{type(error).__name__}: {error}")
    st.stop()


with st.sidebar:
    st.header("Available Tools")
    st.success("🌐 DuckDuckGo Web Search")
    st.success("🌤️ Open-Meteo Weather API")


example = st.selectbox(
    "Example question",
    [
        "Choose an example",
        "What is the current weather in Hyderabad?",
        "Find the best tourist attractions in Goa.",
        (
            "Plan a 2-day trip to Goa. Search for attractions "
            "and check the current weather."
        ),
    ],
)

default_question = ""

if example != "Choose an example":
    default_question = example


with st.form("travel_agent_form"):
    question = st.text_area(
        "Ask the Travel Agent",
        value=default_question,
        height=120,
    )

    submit = st.form_submit_button("Ask Travel Agent")


if submit:
    if not question.strip():
        st.warning("Please enter a travel question.")

    else:
        with st.spinner("The agent is selecting tools..."):
            try:
                answer, tool_history = run_travel_agent(
                    user_query=question,
                    api_key=api_key,
                    model_name=model_name,
                )

                st.subheader("Agent Response")
                st.markdown(answer)

                if tool_history:
                    st.subheader("Tools Used")

                    for index, event in enumerate(
                        tool_history,
                        start=1,
                    ):
                        with st.expander(
                            f"Tool {index}: {event['tool']}",
                            expanded=True,
                        ):
                            st.write("Arguments")
                            st.json(event["arguments"])

                            st.write("Result")
                            st.code(event["result"])
                else:
                    st.info(
                        "The model answered without calling a tool."
                    )

            except Exception as error:
                st.error(
                    "The Travel Agent could not complete the request."
                )
                st.code(f"{type(error).__name__}: {error}")