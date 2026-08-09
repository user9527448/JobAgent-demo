"""Structured JSON logging with request/run context and secret redaction."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

from jobagent.core.config import Settings

REDACTED = "***REDACTED***"
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)

_LOG_CONTEXT: ContextVar[dict[str, object] | None] = ContextVar(
    "jobagent_log_context", default=None
)
_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_secrets(value: object, *, key: str | None = None) -> object:
    """Recursively redact values stored under common secret field names."""
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_secrets(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact_secrets(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Render one JSON object per line for reliable local and hosted ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a record with bound context and sanitized extra fields."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(_LOG_CONTEXT.get() or {})

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
        }
        payload.update(extras)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(redact_secrets(payload), ensure_ascii=False, default=str)


def configure_logging(settings: Settings, *, stream: TextIO | None = None) -> None:
    """Configure the root logger once with deterministic JSON output."""
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)


def get_logger(name: str) -> logging.Logger:
    """Return a standard library logger configured by the application entry point."""
    return logging.getLogger(name)


@contextmanager
def bind_log_context(**fields: object) -> Iterator[None]:
    """Bind correlation fields to logs emitted within the current async context."""
    merged = {**(_LOG_CONTEXT.get() or {}), **fields}
    token = _LOG_CONTEXT.set(merged)
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)
