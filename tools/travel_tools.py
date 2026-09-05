from __future__ import annotations

import os

import requests
from ddgs import DDGS
from dotenv import load_dotenv
from langchain_core.tools import tool
from countryinfo import CountryInfo


load_dotenv(override=True)


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
    """Get current weather for a city using OpenWeatherMap."""

    city = city.strip()

    if not city:
        return "ERROR: The city name is empty."

    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")

        if not api_key:
            return (
                "ERROR: OPENWEATHER_API_KEY is missing "
                "from the environment."
            )

        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": api_key,
                "units": "metric",
            },
            timeout=20,
        )

        if response.status_code == 401:
            return "ERROR: OpenWeatherMap API key is invalid."

        if response.status_code == 404:
            return (
                f"ERROR: Weather location '{city}' "
                "was not found."
            )

        response.raise_for_status()

        data = response.json()

        location_name = data.get("name", city)

        sys_data = data.get("sys", {})
        country = sys_data.get("country", "N/A")

        main = data.get("main", {})

        temperature = main.get("temp", "N/A")
        feels_like = main.get("feels_like", "N/A")
        humidity = main.get("humidity", "N/A")
        pressure = main.get("pressure", "N/A")

        wind = data.get("wind", {})
        wind_speed = wind.get("speed", "N/A")

        weather_list = data.get("weather", [])
        weather = weather_list[0] if weather_list else {}

        condition = weather.get(
            "description",
            "N/A",
        )

        return "\n".join(
            [
                f"Weather for {location_name}, {country}",
                f"Temperature: {temperature}°C",
                f"Feels like: {feels_like}°C",
                f"Condition: {condition.title()}",
                f"Humidity: {humidity}%",
                f"Pressure: {pressure} hPa",
                f"Wind speed: {wind_speed} m/s",
            ]
        )

    except requests.Timeout:
        return "ERROR: The weather service timed out."

    except requests.RequestException as error:
        return (
            "ERROR: The weather service is unavailable. "
            f"{type(error).__name__}: {error}"
        )

    except Exception as error:
        return (
            "ERROR: The weather request could not be processed. "
            f"{type(error).__name__}: {error}"
        )


@tool
def get_country_information(country: str) -> str:
    """Get basic information about a country."""

    country = country.strip()

    if not country:
        return "ERROR: The country name is empty."

    try:
        information = CountryInfo(country).info()

        if not information:
            return (
                f"ERROR: No country information was found "
                f"for '{country}'."
            )

        name_data = information.get("name")

        if isinstance(name_data, dict):
            display_name = (
                name_data.get("common")
                or name_data.get("official")
                or country
            )
        else:
            display_name = name_data or country

        capital_data = information.get("capital", "N/A")

        if isinstance(capital_data, list):
            capital = ", ".join(
                str(item) for item in capital_data
            ) or "N/A"
        else:
            capital = str(capital_data or "N/A")

        currencies_data = information.get(
            "currencies",
            information.get("currency", []),
        )

        if isinstance(currencies_data, list):
            currencies = (
                ", ".join(
                    str(item)
                    for item in currencies_data
                )
                or "N/A"
            )
        elif isinstance(currencies_data, dict):
            currencies = ", ".join(
                str(key)
                for key in currencies_data.keys()
            ) or "N/A"
        else:
            currencies = str(
                currencies_data or "N/A"
            )

        languages_data = information.get(
            "languages",
            [],
        )

        if isinstance(languages_data, list):
            languages = (
                ", ".join(
                    str(language)
                    for language in languages_data
                )
                or "N/A"
            )
        elif isinstance(languages_data, dict):
            languages = ", ".join(
                str(value)
                for value in languages_data.values()
            ) or "N/A"
        else:
            languages = str(
                languages_data or "N/A"
            )

        region = str(
            information.get("region")
            or "N/A"
        )

        subregion = str(
            information.get("subregion")
            or "N/A"
        )

        timezone_data = information.get(
            "timezones",
            [],
        )

        if isinstance(timezone_data, list):
            timezones = (
                ", ".join(
                    str(timezone)
                    for timezone in timezone_data
                )
                or "N/A"
            )
        else:
            timezones = str(
                timezone_data or "N/A"
            )

        return "\n".join(
            [
                f"Country: {display_name}",
                f"Capital: {capital}",
                f"Currency: {currencies}",
                f"Languages: {languages}",
                f"Region: {region}",
                f"Subregion: {subregion}",
                f"Time zones: {timezones}",
            ]
        )

    except KeyError:
        return (
            f"ERROR: No country information was found "
            f"for '{country}'."
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