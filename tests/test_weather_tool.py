import sys

from tools.travel_tools import get_weather


def main() -> None:
    print("Testing Open-Meteo weather tool...")
    print("-" * 50)

    result = get_weather.invoke(
        {
            "city": "Hyderabad",
        }
    )

    print(result)
    print("-" * 50)

    failed_phrases = [
        "Weather error",
        "temporarily unavailable",
        "timed out",
        "Unable to process",
    ]

    if any(
        phrase.lower() in result.lower()
        for phrase in failed_phrases
    ):
        print("RESULT: WEATHER TOOL TEST FAILED")
        sys.exit(1)

    print("RESULT: WEATHER TOOL TEST PASSED")


if __name__ == "__main__":
    main()