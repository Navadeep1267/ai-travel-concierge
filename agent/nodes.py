from __future__ import annotations

import re
import time
from typing import Any, Callable, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.state import TravelAgentState
from monitoring.logger import record_event
from tools.travel_tools import TOOL_MAP, TRAVEL_TOOLS


PLANNER_PROMPT = """
You are the planning component of an AI Travel Concierge.

Choose all tools required to answer the user's request.

Available tools:
- search_web: attractions, restaurants, tourism and current travel facts
- get_weather: current weather, forecast, rain and packing advice
- get_country_information: capital, currency, languages, region and time zones

Use multiple tools when necessary.
Do not invent current information.
"""


def content_to_text(content: Any) -> str:
    """Convert a model response into readable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")

                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))

        return "\n".join(parts)

    return str(content)


def guess_place(query: str) -> str:
    """Try to extract a destination from the user's question."""
    patterns = [
        r"(?:weather|forecast)\s+(?:in|for)\s+([A-Za-z .'-]+)",
        r"(?:trip|travel)\s+to\s+([A-Za-z .'-]+)",
        r"(?:visit|visiting)\s+([A-Za-z .'-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)

        if not match:
            continue

        place = match.group(1)

        place = re.split(
            r"\b(?:and|with|check|search|give|provide|include)\b",
            place,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        place = place.strip(" ,.-")

        if place:
            return place

    return query.strip()


def fallback_tool_calls(query: str) -> list[dict[str, Any]]:
    """Select tools using keywords when model planning is unavailable."""
    lowercase_query = query.lower()
    place = guess_place(query)
    tool_calls: list[dict[str, Any]] = []

    weather_words = {
        "weather",
        "temperature",
        "rain",
        "forecast",
        "packing",
        "pack",
    }

    search_words = {
        "attraction",
        "attractions",
        "tourist",
        "restaurant",
        "restaurants",
        "places",
        "things to do",
        "trip",
        "itinerary",
        "travel",
    }

    country_words = {
        "country",
        "currency",
        "capital",
        "language",
        "languages",
        "region",
        "timezone",
        "time zone",
    }

    if any(word in lowercase_query for word in weather_words):
        tool_calls.append(
            {
                "name": "get_weather",
                "args": {"city": place},
            }
        )

    if any(word in lowercase_query for word in search_words):
        tool_calls.append(
            {
                "name": "search_web",
                "args": {"query": query},
            }
        )

    if any(word in lowercase_query for word in country_words):
        tool_calls.append(
            {
                "name": "get_country_information",
                "args": {"country": place},
            }
        )

    if not tool_calls:
        tool_calls.append(
            {
                "name": "search_web",
                "args": {"query": query},
            }
        )

    return tool_calls


def merge_tool_calls(
    model_calls: list[dict[str, Any]],
    fallback_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine tool calls while removing duplicates."""
    merged: list[dict[str, Any]] = []
    used_names: set[str] = set()

    for call in model_calls + fallback_calls:
        name = str(call.get("name", "")).strip()

        if not name or name in used_names:
            continue

        merged.append(
            {
                "name": name,
                "args": call.get("args", {}),
            }
        )

        used_names.add(name)

    return merged


def execute_one_tool(tool_call: dict[str, Any]) -> str:
    """Execute one selected LangChain tool safely."""
    tool_name = str(tool_call.get("name", "")).strip()
    arguments = tool_call.get("args", {})

    selected_tool = TOOL_MAP.get(tool_name)

    if selected_tool is None:
        return f"ERROR: Unknown tool '{tool_name}'."

    try:
        return str(selected_tool.invoke(arguments))

    except Exception as error:
        return (
            f"ERROR: Tool '{tool_name}' failed. "
            f"{type(error).__name__}: {error}"
        )


def is_error_result(result: str) -> bool:
    """Check whether a tool result represents failure."""
    return result.strip().upper().startswith("ERROR:")


def validate_results(
    results: dict[str, str],
    retry_count: int,
    max_retries: int,
) -> str:
    """Return success, retry or failed."""
    if not results:
        return "retry" if retry_count < max_retries else "failed"

    failures = [
        result
        for result in results.values()
        if is_error_result(result)
    ]

    if not failures:
        return "success"

    # Continue when at least one tool returned useful information.
    if len(failures) < len(results):
        return "success"

    if retry_count < max_retries:
        return "retry"

    return "failed"


def create_agent_nodes(
    api_key: str,
    model_name: str,
) -> dict[str, Callable[..., Any]]:
    """Create all nodes used by the LangGraph workflow."""
    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
    )

    model_with_tools = model.bind_tools(TRAVEL_TOOLS)

    def planner_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        query = state.get("user_query", "").strip()
        errors = list(state.get("errors", []))
        model_calls: list[dict[str, Any]] = []

        try:
            response = model_with_tools.invoke(
                [
                    SystemMessage(content=PLANNER_PROMPT),
                    HumanMessage(content=query),
                ]
            )

            raw_calls = getattr(response, "tool_calls", None) or []

            for call in raw_calls:
                if isinstance(call, dict):
                    model_calls.append(
                        {
                            "name": call.get("name", ""),
                            "args": call.get("args", {}),
                        }
                    )

        except Exception as error:
            errors.append(
                "Planner model failed. Keyword fallback planning "
                f"was used. {type(error).__name__}: {error}"
            )

            record_event(
                "planner_error",
                error_type=type(error).__name__,
            )

        selected_tools = merge_tool_calls(
            model_calls,
            fallback_tool_calls(query),
        )

        record_event(
            "planner_completed",
            selected_tools=[
                call["name"]
                for call in selected_tools
            ],
        )

        return {
            "selected_tools": selected_tools,
            "errors": errors,
        }

    def tools_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        results: dict[str, str] = {}
        errors = list(state.get("errors", []))

        for tool_call in state.get("selected_tools", []):
            tool_name = str(tool_call.get("name", ""))
            started = time.perf_counter()

            result = execute_one_tool(tool_call)
            duration = time.perf_counter() - started
            success = not is_error_result(result)

            results[tool_name] = result

            if not success:
                errors.append(result)

            record_event(
                "tool_call",
                tool=tool_name,
                success=success,
                duration_seconds=round(duration, 4),
            )

        return {
            "tool_results": results,
            "errors": errors,
        }

    def validation_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        status = validate_results(
            results=state.get("tool_results", {}),
            retry_count=state.get("retry_count", 0),
            max_retries=state.get("max_retries", 2),
        )

        record_event(
            "validation_completed",
            status=status,
            retry_count=state.get("retry_count", 0),
        )

        return {
            "validation_status": status,
        }

    def retry_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        retry_count = state.get("retry_count", 0) + 1

        record_event(
            "agent_retry",
            retry_count=retry_count,
        )

        return {
            "retry_count": retry_count,
            "selected_tools": fallback_tool_calls(
                state.get("user_query", "")
            ),
        }

    def response_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        query = state.get("user_query", "")
        tool_results = state.get("tool_results", {})

        context = "\n\n".join(
            f"{tool_name}:\n{result}"
            for tool_name, result in tool_results.items()
        )

        prompt = f"""
Create a clear travel answer using only the verified tool results.

Rules:
- Do not invent current facts.
- Include source links returned by the web-search tool.
- Clearly state when information is unavailable.
- Give practical itinerary and packing advice.
- Use headings and readable formatting.

User request:
{query}

Tool results:
{context}
"""

        try:
            response = model.invoke(
                [
                    SystemMessage(
                        content=(
                            "You are an accurate AI Travel Concierge."
                        )
                    ),
                    HumanMessage(content=prompt),
                ]
            )

            answer = content_to_text(response.content).strip()

            if not answer:
                answer = context

        except Exception as error:
            answer = (
                "The response model was unavailable. "
                "Verified tool results are shown below.\n\n"
                f"{context}"
            )

            record_event(
                "response_model_error",
                error_type=type(error).__name__,
            )

        total_duration = (
            time.perf_counter()
            - state.get("start_time", time.perf_counter())
        )

        record_event(
            "agent_completed",
            success=True,
            duration_seconds=round(total_duration, 4),
            tools_used=list(tool_results.keys()),
            retry_count=state.get("retry_count", 0),
        )

        return {
            "final_answer": answer,
            "total_duration": total_duration,
        }

    def error_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        total_duration = (
            time.perf_counter()
            - state.get("start_time", time.perf_counter())
        )

        record_event(
            "agent_completed",
            success=False,
            duration_seconds=round(total_duration, 4),
            retry_count=state.get("retry_count", 0),
        )

        return {
            "final_answer": (
                "The Travel Agent could not retrieve enough verified "
                "information after several attempts. Check the "
                "destination name and try again."
            ),
            "total_duration": total_duration,
        }

    return {
        "planner": planner_node,
        "tools": tools_node,
        "validator": validation_node,
        "retry": retry_node,
        "response": response_node,
        "error": error_node,
    }


def route_after_validation(
    state: TravelAgentState,
) -> Literal["response", "retry", "error"]:
    """Choose the next graph node after result validation."""
    status = state.get("validation_status", "failed")

    if status == "success":
        return "response"

    if status == "retry":
        return "retry"

    return "error"