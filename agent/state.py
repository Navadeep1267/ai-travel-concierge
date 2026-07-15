from __future__ import annotations

from typing import Any, TypedDict


class TravelAgentState(TypedDict, total=False):
    user_query: str
    messages: list[dict[str, str]]
    selected_tools: list[dict[str, Any]]
    tool_results: dict[str, str]
    errors: list[str]
    retry_count: int
    max_retries: int
    validation_status: str
    final_answer: str
    start_time: float
    total_duration: float