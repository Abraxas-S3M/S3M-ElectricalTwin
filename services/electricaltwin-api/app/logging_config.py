"""Structured JSON logging for the ElectricalTwin API service.

The service emits one JSON object per log line on stdout. There are no ``print``
statements anywhere in the service; all diagnostic output flows through the
standard library :mod:`logging` machinery configured here.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_RESERVED = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonLogFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Preserve any structured ``extra`` fields supplied at call sites.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Install the JSON formatter on the service logger and return it."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    logger = logging.getLogger("electricaltwin.api")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger
