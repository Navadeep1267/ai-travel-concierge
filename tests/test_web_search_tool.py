import sys

from tools.travel_tools import search_web


def main() -> None:
    print("Testing DuckDuckGo web-search tool...")
    print("-" * 50)

    result = search_web.invoke(
        {
            "query": (
                "top tourist attractions in Hyderabad India"
            ),
        }
    )

    print(result)
    print("-" * 50)

    failed_phrases = [
        "Web search error",
        "temporarily unavailable",
        "No web-search results",
    ]

    if any(
        phrase.lower() in result.lower()
        for phrase in failed_phrases
    ):
        print("RESULT: WEB-SEARCH TOOL TEST FAILED")
        sys.exit(1)

    print("RESULT: WEB-SEARCH TOOL TEST PASSED")


if __name__ == "__main__":
    main()