from agent.nodes import (
    execute_one_tool,
    fallback_tool_calls,
    route_after_validation,
    validate_results,
)
from tools.travel_tools import (
    TOOL_MAP,
    get_country_information,
    get_weather,
)


def selected_tool_names(query: str) -> set[str]:
    return {
        tool_call["name"]
        for tool_call in fallback_tool_calls(query)
    }


def test_three_tools_are_registered():
    assert set(TOOL_MAP.keys()) == {
        "search_web",
        "get_weather",
        "get_country_information",
    }


def test_weather_tool_is_selected():
    names = selected_tool_names(
        "What is the weather in Hyderabad?"
    )

    assert "get_weather" in names


def test_all_three_tools_are_selected():
    names = selected_tool_names(
        "Plan a trip to Japan, check the weather, "
        "search for attractions and provide currency information."
    )

    assert "search_web" in names
    assert "get_weather" in names
    assert "get_country_information" in names


def test_empty_weather_city_is_handled():
    result = get_weather.invoke({"city": ""})

    assert result.startswith("ERROR:")


def test_empty_country_is_handled():
    result = get_country_information.invoke({"country": ""})

    assert result.startswith("ERROR:")


def test_unknown_tool_is_handled():
    result = execute_one_tool(
        {
            "name": "unknown_tool",
            "args": {},
        }
    )

    assert result.startswith("ERROR:")


def test_validation_success():
    result = validate_results(
        {"get_weather": "Weather information"},
        retry_count=0,
        max_retries=2,
    )

    assert result == "success"


def test_validation_retry_and_failure():
    retry_result = validate_results(
        {"get_weather": "ERROR: unavailable"},
        retry_count=0,
        max_retries=2,
    )

    failed_result = validate_results(
        {"get_weather": "ERROR: unavailable"},
        retry_count=2,
        max_retries=2,
    )

    assert retry_result == "retry"
    assert failed_result == "failed"


def test_graph_routing():
    assert route_after_validation(
        {"validation_status": "success"}
    ) == "response"

    assert route_after_validation(
        {"validation_status": "retry"}
    ) == "retry"

    assert route_after_validation(
        {"validation_status": "failed"}
    ) == "error"
