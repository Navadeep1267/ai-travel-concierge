from __future__ import annotations

from typing import Any

import requests
from ddgs import DDGS
from langchain_core.tools import tool


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy with frost",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Heavy thunderstorm with hail",
}


def _safe_value(values: list[Any], index: int, default: Any = "N/A") -> Any:
    """Safely read an item from a list."""
    if index < len(values):
        return values[index]

    return default


@tool
def search_web(query: str) -> str:
    """
    Search the web for current travel information.

    Use this tool for attractions, restaurants, tourism information,
    travel news, things to do, destination guides and current events.
    """
    cleaned_query = query.strip()

    if not cleaned_query:
        return "Web search error: the search query cannot be empty."

    try:
        search_results = list(
            DDGS().text(
                cleaned_query,
                max_results=5,
            )
        )

        if not search_results:
            return (
                "No web-search results were found. "
                "Try using a clearer destination or search query."
            )

        formatted_results = []

        for index, result in enumerate(search_results, start=1):
            title = result.get("title", "Untitled result")
            description = (
                result.get("body")
                or result.get("description")
                or "No description available."
            )
            link = (
                result.get("href")
                or result.get("url")
                or "No link available."
            )

            formatted_results.append(
                "\n".join(
                    [
                        f"Result {index}: {title}",
                        f"Description: {description}",
                        f"Source: {link}",
                    ]
                )
            )

        return "\n\n".join(formatted_results)

    except Exception as error:
        return (
            "Web search is temporarily unavailable. "
            f"Technical details: {type(error).__name__}: {error}"
        )


@tool
def get_weather(city: str) -> str:
    """
    Get current weather and a short forecast for a city.

    Use this tool when the user asks about temperature, rain,
    climate, weather forecast, packing advice or travel conditions.
    """
    cleaned_city = city.strip()

    if not cleaned_city:
        return "Weather error: the city name cannot be empty."

    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    try:
        location_response = requests.get(
            geocoding_url,
            params={
                "name": cleaned_city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=15,
        )

        location_response.raise_for_status()
        location_results = location_response.json().get(
            "results",
            [],
        )

        if not location_results:
            return (
                f"Weather error: no location was found for "
                f"'{cleaned_city}'."
            )

        location = location_results[0]

        latitude = location["latitude"]
        longitude = location["longitude"]
        location_name = location.get("name", cleaned_city)
        country = location.get("country", "")

        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
        )

        weather_response = requests.get(
            forecast_url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "timezone": "auto",
                "forecast_days": 3,
            },
            timeout=15,
        )

        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        current_code = current.get("weather_code")
        current_condition = WEATHER_CODES.get(
            current_code,
            f"Weather code {current_code}",
        )

        output_lines = [
            f"Weather for {location_name}, {country}",
            (
                "Current temperature: "
                f"{current.get('temperature_2m', 'N/A')} °C"
            ),
            (
                "Feels like: "
                f"{current.get('apparent_temperature', 'N/A')} °C"
            ),
            f"Condition: {current_condition}",
            (
                "Wind speed: "
                f"{current.get('wind_speed_10m', 'N/A')} km/h"
            ),
            "",
            "Three-day forecast:",
        ]

        dates = daily.get("time", [])
        maximum_temperatures = daily.get(
            "temperature_2m_max",
            [],
        )
        minimum_temperatures = daily.get(
            "temperature_2m_min",
            [],
        )
        rain_probabilities = daily.get(
            "precipitation_probability_max",
            [],
        )
        daily_codes = daily.get("weather_code", [])

        for index, forecast_date in enumerate(dates):
            daily_condition = WEATHER_CODES.get(
                _safe_value(daily_codes, index),
                "Unknown condition",
            )

            maximum = _safe_value(
                maximum_temperatures,
                index,
            )
            minimum = _safe_value(
                minimum_temperatures,
                index,
            )
            rain_probability = _safe_value(
                rain_probabilities,
                index,
            )

            output_lines.append(
                (
                    f"{forecast_date}: {daily_condition}, "
                    f"minimum {minimum} °C, maximum {maximum} °C, "
                    f"rain probability {rain_probability}%"
                )
            )

        return "\n".join(output_lines)

    except requests.Timeout:
        return (
            "Weather service timed out. "
            "Please try again after a few seconds."
        )

    except requests.RequestException as error:
        return (
            "Weather service is temporarily unavailable. "
            f"Technical details: {error}"
        )

    except Exception as error:
        return (
            "Unable to process the weather request. "
            f"Technical details: {type(error).__name__}: {error}"
        )