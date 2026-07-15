from __future__ import annotations

import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    create_agent_nodes,
    route_after_validation,
)
from agent.state import TravelAgentState


def build_travel_graph(
    api_key: str,
    model_name: str,
):
    """Create and compile the LangGraph travel-agent workflow."""
    nodes = create_agent_nodes(
        api_key=api_key,
        model_name=model_name,
    )

    workflow = StateGraph(TravelAgentState)

    workflow.add_node("planner", nodes["planner"])
    workflow.add_node("tools", nodes["tools"])
    workflow.add_node("validator", nodes["validator"])
    workflow.add_node("retry", nodes["retry"])
    workflow.add_node("response", nodes["response"])
    workflow.add_node("error", nodes["error"])

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "tools")
    workflow.add_edge("tools", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "response": "response",
            "retry": "retry",
            "error": "error",
        },
    )

    workflow.add_edge("retry", "tools")
    workflow.add_edge("response", END)
    workflow.add_edge("error", END)

    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)


def run_travel_graph(
    graph: Any,
    user_query: str,
    thread_id: str,
    message_history: list[dict[str, str]],
) -> TravelAgentState:
    """Run one user request through the compiled workflow."""
    query = user_query.strip()

    if not query:
        raise ValueError("The user query cannot be empty.")

    initial_state: TravelAgentState = {
        "user_query": query,
        "messages": message_history,
        "selected_tools": [],
        "tool_results": {},
        "errors": [],
        "retry_count": 0,
        "max_retries": 2,
        "validation_status": "",
        "final_answer": "",
        "start_time": time.perf_counter(),
        "total_duration": 0.0,
    }

    result = graph.invoke(
        initial_state,
        config={
            "configurable": {
                "thread_id": thread_id,
            }
        },
    )

    return result