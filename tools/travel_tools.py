from __future__ import annotations

from urllib.parse import quote

import requests
from ddgs import DDGS
from langchain_core.tools import tool


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog with frost",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Heavy thunderstorm with hail",
}


@tool
def search_web(query: str) -> str:
    """Search the web for current travel information and sources."""
    query = query.strip()

    if not query:
        return "ERROR: The web-search query is empty."

    try:
        results = list(
            DDGS().text(
                query,
                max_results=5,
            )
        )

        if not results:
            return "ERROR: No web-search results were found."

        formatted_results = []

        for number, result in enumerate(results, start=1):
            title = result.get("title", "Untitled result")
            description = (
                result.get("body")
                or result.get("description")
                or "No description available."
            )
            source = (
                result.get("href")
                or result.get("url")
                or "No source URL available."
            )

            formatted_results.append(
                "\n".join(
                    [
                        f"Result {number}: {title}",
                        f"Description: {description}",
                        f"Source: {source}",
                    ]
                )
            )

        return "\n\n".join(formatted_results)

    except Exception as error:
        return (
            "ERROR: Web search is temporarily unavailable. "
            f"{type(error).__name__}: {error}"
        )


@tool
def get_weather(city: str) -> str:
    """Get current weather and a three-day forecast for a city."""
    city = city.strip()

    if not city:
        return "ERROR: The city name is empty."

    try:
        location_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=15,
        )
        location_response.raise_for_status()

        locations = location_response.json().get("results", [])

        if not locations:
            return f"ERROR: No location was found for '{city}'."

        location = locations[0]

        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
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

        weather_code = current.get("weather_code")
        condition = WEATHER_CODES.get(
            weather_code,
            f"Weather code {weather_code}",
        )

        location_name = location.get("name", city)
        country = location.get("country", "")

        lines = [
            f"Weather for {location_name}, {country}",
            (
                "Current temperature: "
                f"{current.get('temperature_2m', 'N/A')} °C"
            ),
            (
                "Feels like: "
                f"{current.get('apparent_temperature', 'N/A')} °C"
            ),
            f"Condition: {condition}",
            (
                "Wind speed: "
                f"{current.get('wind_speed_10m', 'N/A')} km/h"
            ),
            "",
            "Three-day forecast:",
        ]

        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        maximums = daily.get("temperature_2m_max", [])
        minimums = daily.get("temperature_2m_min", [])
        rain_values = daily.get(
            "precipitation_probability_max",
            [],
        )

        for index, forecast_date in enumerate(dates):
            forecast_code = (
                codes[index]
                if index < len(codes)
                else None
            )

            forecast_condition = WEATHER_CODES.get(
                forecast_code,
                "Unknown weather",
            )

            maximum = (
                maximums[index]
                if index < len(maximums)
                else "N/A"
            )

            minimum = (
                minimums[index]
                if index < len(minimums)
                else "N/A"
            )

            rain = (
                rain_values[index]
                if index < len(rain_values)
                else "N/A"
            )

            lines.append(
                f"{forecast_date}: {forecast_condition}, "
                f"minimum {minimum} °C, "
                f"maximum {maximum} °C, "
                f"rain probability {rain}%"
            )

        return "\n".join(lines)

    except requests.Timeout:
        return "ERROR: The weather service timed out."

    except requests.RequestException as error:
        return (
            "ERROR: The weather service is unavailable. "
            f"{error}"
        )

    except Exception as error:
        return (
            "ERROR: The weather request could not be processed. "
            f"{type(error).__name__}: {error}"
        )


@tool
def get_country_information(country: str) -> str:
    """Get a country's capital, currency, languages and time zones."""
    country = country.strip()

    if not country:
        return "ERROR: The country name is empty."

    try:
        response = requests.get(
            (
                "https://restcountries.com/v3.1/name/"
                f"{quote(country)}"
            ),
            params={
                "fields": (
                    "name,capital,currencies,languages,"
                    "region,subregion,timezones"
                )
            },
            timeout=15,
        )
        response.raise_for_status()

        results = response.json()

        if not results:
            return (
                f"ERROR: No country information was found "
                f"for '{country}'."
            )

        information = results[0]

        official_name = information.get(
            "name",
            {},
        ).get("official", country)

        capitals = information.get("capital", [])
        capital = ", ".join(capitals) if capitals else "N/A"

        currency_items = []

        for currency_code, details in information.get(
            "currencies",
            {},
        ).items():
            currency_name = details.get(
                "name",
                currency_code,
            )
            currency_symbol = details.get("symbol", "")

            currency_items.append(
                f"{currency_name} "
                f"({currency_code}) "
                f"{currency_symbol}".strip()
            )

        currencies = (
            ", ".join(currency_items)
            if currency_items
            else "N/A"
        )

        language_values = list(
            information.get("languages", {}).values()
        )

        languages = (
            ", ".join(language_values)
            if language_values
            else "N/A"
        )

        region = information.get("region", "N/A")
        subregion = information.get("subregion", "N/A")

        timezones = ", ".join(
            information.get("timezones", [])
        ) or "N/A"

        return "\n".join(
            [
                f"Country: {official_name}",
                f"Capital: {capital}",
                f"Currency: {currencies}",
                f"Languages: {languages}",
                f"Region: {region}",
                f"Subregion: {subregion}",
                f"Time zones: {timezones}",
            ]
        )

    except requests.Timeout:
        return "ERROR: The country-information service timed out."

    except requests.RequestException as error:
        return (
            "ERROR: The country-information service is unavailable. "
            f"{error}"
        )

    except Exception as error:
        return (
            "ERROR: Country information could not be processed. "
            f"{type(error).__name__}: {error}"
        )


TRAVEL_TOOLS = [
    search_web,
    get_weather,
    get_country_information,
]


TOOL_MAP = {
    travel_tool.name: travel_tool
    for travel_tool in TRAVEL_TOOLS
}