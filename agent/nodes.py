from __future__ import annotations

import re
import time
from typing import Any, Callable, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.state import TravelAgentState
from monitoring.logger import record_event
from tools.travel_tools import TOOL_MAP


FINAL_RESPONSE_PROMPT = """
You are an accurate AI Travel Concierge.

Create a clear and useful travel response using only the verified tool
results provided to you.

Rules:
- Do not invent current information.
- Include source URLs returned by the web-search tool.
- Mention unavailable information clearly.
- Give practical itinerary and packing advice.
- Use readable headings and short paragraphs.
- Do not claim that a failed tool returned valid information.
"""


def content_to_text(content: Any) -> str:
    """Convert a Gemini response into readable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

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
    """Extract a likely destination from the user's question."""
    patterns = [
        r"(?:trip|travel|journey|visit)\s+to\s+([A-Za-z .'-]+)",
        r"(?:weather|forecast)\s+(?:in|for)\s+([A-Za-z .'-]+)",
        r"(?:visiting|visit)\s+([A-Za-z .'-]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            query,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        place = match.group(1)

        place = re.split(
            (
                r"\b(?:and|with|check|search|find|give|provide|"
                r"include|tell|show|plan)\b"
            ),
            place,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        place = place.strip(" ,.-")

        if place:
            return place

    words = query.strip().split()

    if words:
        return " ".join(words[-3:]).strip(" ,.-")

    return query.strip()


def fallback_tool_calls(
    query: str,
) -> list[dict[str, Any]]:
    """
    Select tools using keywords.

    This planner does not call Gemini, which reduces API usage
    and avoids unnecessary quota errors.
    """
    lowercase_query = query.lower()
    place = guess_place(query)

    tool_calls: list[dict[str, Any]] = []

    weather_words = {
        "weather",
        "temperature",
        "rain",
        "forecast",
        "climate",
        "packing",
        "pack",
        "umbrella",
    }

    search_words = {
        "attraction",
        "attractions",
        "tourist",
        "tourism",
        "restaurant",
        "restaurants",
        "places",
        "things to do",
        "trip",
        "itinerary",
        "travel",
        "visit",
        "hotel",
        "hotels",
        "activity",
        "activities",
        "search",
        "find",
    }

    country_words = {
        "country",
        "currency",
        "capital",
        "language",
        "languages",
        "region",
        "subregion",
        "timezone",
        "time zone",
        "international",
    }

    if any(
        word in lowercase_query
        for word in weather_words
    ):
        tool_calls.append(
            {
                "name": "get_weather",
                "args": {
                    "city": place,
                },
            }
        )

    if any(
        word in lowercase_query
        for word in search_words
    ):
        tool_calls.append(
            {
                "name": "search_web",
                "args": {
                    "query": query,
                },
            }
        )

    if any(
        word in lowercase_query
        for word in country_words
    ):
        tool_calls.append(
            {
                "name": "get_country_information",
                "args": {
                    "country": place,
                },
            }
        )

    if not tool_calls:
        tool_calls.append(
            {
                "name": "search_web",
                "args": {
                    "query": query,
                },
            }
        )

    return tool_calls


def merge_tool_calls(
    first_calls: list[dict[str, Any]],
    second_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine tool calls while removing duplicate tool names."""
    merged: list[dict[str, Any]] = []
    used_names: set[str] = set()

    for tool_call in first_calls + second_calls:
        tool_name = str(
            tool_call.get("name", "")
        ).strip()

        if not tool_name:
            continue

        if tool_name in used_names:
            continue

        merged.append(
            {
                "name": tool_name,
                "args": tool_call.get("args", {}),
            }
        )

        used_names.add(tool_name)

    return merged


def execute_one_tool(
    tool_call: dict[str, Any],
) -> str:
    """Execute one selected travel tool safely."""
    tool_name = str(
        tool_call.get("name", "")
    ).strip()

    arguments = tool_call.get("args", {})

    selected_tool = TOOL_MAP.get(tool_name)

    if selected_tool is None:
        return f"ERROR: Unknown tool '{tool_name}'."

    try:
        result = selected_tool.invoke(arguments)
        return str(result)

    except Exception as error:
        return (
            f"ERROR: Tool '{tool_name}' failed. "
            f"{type(error).__name__}: {error}"
        )


def is_error_result(result: str) -> bool:
    """Check whether a tool result represents an error."""
    return result.strip().upper().startswith(
        "ERROR:"
    )


def validate_results(
    results: dict[str, str],
    retry_count: int,
    max_retries: int,
) -> str:
    """Return success, retry or failed."""
    if not results:
        if retry_count < max_retries:
            return "retry"

        return "failed"

    failed_results = [
        result
        for result in results.values()
        if is_error_result(result)
    ]

    if not failed_results:
        return "success"

    # Continue when at least one tool returned useful information.
    if len(failed_results) < len(results):
        return "success"

    if retry_count < max_retries:
        return "retry"

    return "failed"


def create_fallback_answer(
    query: str,
    tool_results: dict[str, str],
) -> str:
    """
    Create an answer without Gemini.

    This is used when Gemini quota is exceeded or the model
    is temporarily unavailable.
    """
    lines = [
        "## Travel information",
        "",
        (
            "The AI summary is temporarily unavailable, but the "
            "verified tool results are shown below."
        ),
        "",
        f"**Your request:** {query}",
        "",
    ]

    for tool_name, result in tool_results.items():
        readable_name = tool_name.replace(
            "_",
            " ",
        ).title()

        lines.extend(
            [
                f"### {readable_name}",
                result,
                "",
            ]
        )

    lines.extend(
        [
            "### General advice",
            (
                "Confirm opening times, ticket availability and "
                "local travel restrictions before departure."
            ),
        ]
    )

    return "\n".join(lines)


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

    def planner_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """
        Select tools without calling Gemini.

        This saves Gemini quota and prevents planner failures
        caused by free-tier request limits.
        """
        query = state.get(
            "user_query",
            "",
        ).strip()

        errors = list(
            state.get(
                "errors",
                [],
            )
        )

        if not query:
            errors.append(
                "The user question is empty."
            )

            return {
                "selected_tools": [],
                "errors": errors,
            }

        selected_tools = fallback_tool_calls(query)

        record_event(
            "planner_completed",
            selected_tools=[
                tool_call["name"]
                for tool_call in selected_tools
            ],
            planning_mode="keyword_planner",
        )

        return {
            "selected_tools": selected_tools,
            "errors": errors,
        }

    def tools_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """Execute all tools selected by the planner."""
        results: dict[str, str] = {}

        errors = list(
            state.get(
                "errors",
                [],
            )
        )

        selected_tools = state.get(
            "selected_tools",
            [],
        )

        for tool_call in selected_tools:
            tool_name = str(
                tool_call.get(
                    "name",
                    "",
                )
            )

            started = time.perf_counter()

            result = execute_one_tool(
                tool_call
            )

            duration = (
                time.perf_counter()
                - started
            )

            success = not is_error_result(
                result
            )

            results[tool_name] = result

            if not success:
                errors.append(result)

            record_event(
                "tool_call",
                tool=tool_name,
                success=success,
                duration_seconds=round(
                    duration,
                    4,
                ),
            )

        return {
            "tool_results": results,
            "errors": errors,
        }

    def validation_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """Validate tool results and choose the next action."""
        status = validate_results(
            results=state.get(
                "tool_results",
                {},
            ),
            retry_count=state.get(
                "retry_count",
                0,
            ),
            max_retries=state.get(
                "max_retries",
                2,
            ),
        )

        record_event(
            "validation_completed",
            status=status,
            retry_count=state.get(
                "retry_count",
                0,
            ),
        )

        return {
            "validation_status": status,
        }

    def retry_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """Retry failed tool calls."""
        retry_count = (
            state.get(
                "retry_count",
                0,
            )
            + 1
        )

        selected_tools = fallback_tool_calls(
            state.get(
                "user_query",
                "",
            )
        )

        record_event(
            "agent_retry",
            retry_count=retry_count,
            selected_tools=[
                tool_call["name"]
                for tool_call in selected_tools
            ],
        )

        return {
            "retry_count": retry_count,
            "selected_tools": selected_tools,
        }

    def response_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """Generate the final answer using one Gemini call."""
        query = state.get(
            "user_query",
            "",
        )

        tool_results = state.get(
            "tool_results",
            {},
        )

        context_sections: list[str] = []

        for tool_name, result in tool_results.items():
            context_sections.append(
                (
                    f"TOOL: {tool_name}\n"
                    f"RESULT:\n{result}"
                )
            )

        context = "\n\n".join(
            context_sections
        )

        prompt = f"""
User request:
{query}

Verified tool results:
{context}

Create the final travel response.
"""

        try:
            response = model.invoke(
                [
                    SystemMessage(
                        content=FINAL_RESPONSE_PROMPT
                    ),
                    HumanMessage(
                        content=prompt
                    ),
                ]
            )

            answer = content_to_text(
                response.content
            ).strip()

            if not answer:
                answer = create_fallback_answer(
                    query=query,
                    tool_results=tool_results,
                )

        except Exception as error:
            answer = create_fallback_answer(
                query=query,
                tool_results=tool_results,
            )

            error_message = str(error).lower()

            if (
                "resource_exhausted"
                in error_message
                or "429" in error_message
                or "quota" in error_message
            ):
                record_event(
                    "response_quota_exceeded",
                    error_type=type(
                        error
                    ).__name__,
                )
            else:
                record_event(
                    "response_model_error",
                    error_type=type(
                        error
                    ).__name__,
                )

        total_duration = (
            time.perf_counter()
            - state.get(
                "start_time",
                time.perf_counter(),
            )
        )

        record_event(
            "agent_completed",
            success=True,
            duration_seconds=round(
                total_duration,
                4,
            ),
            tools_used=list(
                tool_results.keys()
            ),
            retry_count=state.get(
                "retry_count",
                0,
            ),
        )

        return {
            "final_answer": answer,
            "total_duration": total_duration,
        }

    def error_node(
        state: TravelAgentState,
    ) -> dict[str, Any]:
        """Return a friendly message after all retries fail."""
        total_duration = (
            time.perf_counter()
            - state.get(
                "start_time",
                time.perf_counter(),
            )
        )

        record_event(
            "agent_completed",
            success=False,
            duration_seconds=round(
                total_duration,
                4,
            ),
            retry_count=state.get(
                "retry_count",
                0,
            ),
        )

        return {
            "final_answer": (
                "The Travel Agent could not retrieve enough "
                "verified information after several attempts. "
                "Please check the destination name and try again."
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
    """Choose the next node after tool-result validation."""
    status = state.get(
        "validation_status",
        "failed",
    )

    if status == "success":
        return "response"

    if status == "retry":
        return "retry"

    return "error"