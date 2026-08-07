"""Structured JSON logging for the ElectricalTwin API.

The service emits one JSON object per log line and never uses ``print``. A
minimal, dependency-free formatter keeps the log schema stable and greppable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_RESERVED = frozenset(vars(logging.makeLogRecord({})).keys())


class JsonLogFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure the root logger for structured JSON output and return it."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    return root
