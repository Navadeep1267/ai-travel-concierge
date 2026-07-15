from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIRECTORY = PROJECT_ROOT / "logs"
LOGS_DIRECTORY.mkdir(parents=True, exist_ok=True)

AGENT_LOG_FILE = LOGS_DIRECTORY / "agent.log"
METRICS_FILE = LOGS_DIRECTORY / "metrics.jsonl"


logger = logging.getLogger("travel_agent")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        AGENT_LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def protect_sensitive_data(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Remove sensitive values before writing logs."""
    protected_words = {
        "key",
        "token",
        "secret",
        "password",
    }

    safe_data: dict[str, Any] = {}

    for field_name, field_value in data.items():
        lowercase_name = field_name.lower()

        contains_sensitive_word = any(
            word in lowercase_name
            for word in protected_words
        )

        if contains_sensitive_word:
            safe_data[field_name] = "[REDACTED]"
        else:
            safe_data[field_name] = field_value

    return safe_data


def record_event(
    event: str,
    **data: Any,
) -> None:
    """Record one monitoring event."""
    safe_data = protect_sensitive_data(data)

    entry = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "event": event,
        **safe_data,
    }

    logger.info(
        "%s | %s",
        event,
        safe_data,
    )

    with METRICS_FILE.open(
        "a",
        encoding="utf-8",
    ) as metrics_file:
        metrics_file.write(
            json.dumps(
                entry,
                default=str,
            )
            + "\n"
        )


def read_events(
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Read recent monitoring events."""
    if not METRICS_FILE.exists():
        return []

    events: list[dict[str, Any]] = []

    with METRICS_FILE.open(
        "r",
        encoding="utf-8",
    ) as metrics_file:
        for line in metrics_file:
            line = line.strip()

            if not line:
                continue

            try:
                events.append(
                    json.loads(line)
                )
            except json.JSONDecodeError:
                continue

    return events[-limit:]