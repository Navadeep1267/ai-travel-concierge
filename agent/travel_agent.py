from __future__ import annotations

from typing import Any

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from tools.travel_tools import get_weather, search_web


TOOLS = [
    search_web,
    get_weather,
]

TOOL_MAP = {
    tool.name: tool
    for tool in TOOLS
}


SYSTEM_PROMPT = """
You are an AI Travel Concierge.

Your job is to provide useful and accurate travel assistance.

Available tools:

1. search_web
   Use it for attractions, places to visit, restaurants,
   tourism information, current travel information and sources.

2. get_weather
   Use it for temperature, rain, forecast, packing advice
   and travel-weather conditions.

Important rules:

- Use tools instead of inventing current information.
- When a request asks for both attractions and weather,
  call both tools before answering.
- Clearly separate live information from general suggestions.
- Include source links returned by the web-search tool.
- Explain API or tool failures in simple language.
- Never invent flight prices, hotel availability or live facts.
- Give practical, concise and well-structured travel advice.
"""


def _content_to_text(content: Any) -> str:
    """Convert model content into displayable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")

                if text:
                    text_parts.append(str(text))
            else:
                text_parts.append(str(item))

        return "\n".join(text_parts)

    return str(content)


def run_travel_agent(
    user_query: str,
    api_key: str,
    model_name: str,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Run the LangChain travel agent.

    Returns:
        Final answer and a list describing every tool call.
    """
    cleaned_query = user_query.strip()

    if not cleaned_query:
        raise ValueError("The user question cannot be empty.")

    if not api_key:
        raise ValueError("The Gemini API key is missing.")

    if not model_name:
        raise ValueError("The Gemini model name is missing.")

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
    )

    model_with_tools = model.bind_tools(TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=cleaned_query),
    ]

    tool_history: list[dict[str, Any]] = []

    try:
        response = model_with_tools.invoke(messages)

        maximum_iterations = 4

        for _ in range(maximum_iterations):
            tool_calls = getattr(
                response,
                "tool_calls",
                None,
            ) or []

            if not tool_calls:
                final_answer = _content_to_text(
                    response.content
                )

                if not final_answer.strip():
                    final_answer = (
                        "The agent completed the request but "
                        "did not return a readable answer."
                    )

                return final_answer, tool_history

            messages.append(response)

            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_arguments = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", "")

                selected_tool = TOOL_MAP.get(tool_name)

                if selected_tool is None:
                    tool_result = (
                        f"Tool error: '{tool_name}' "
                        "is not an available tool."
                    )

                else:
                    try:
                        tool_result = selected_tool.invoke(
                            tool_arguments
                        )

                    except Exception as error:
                        tool_result = (
                            f"The tool '{tool_name}' failed. "
                            f"Technical details: "
                            f"{type(error).__name__}: {error}"
                        )

                tool_history.append(
                    {
                        "tool": tool_name,
                        "arguments": tool_arguments,
                        "result": str(tool_result),
                    }
                )

                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call_id,
                    )
                )

            response = model_with_tools.invoke(messages)

        return (
            "The agent stopped because it reached the "
            "maximum number of tool-calling steps.",
            tool_history,
        )

    except Exception as error:
        raise RuntimeError(
            "The travel agent could not complete the request. "
            f"{type(error).__name__}: {error}"
        ) from error