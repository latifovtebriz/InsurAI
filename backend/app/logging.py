"""Structured JSON logging configuration and correlation context."""

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ContextVar for propagating correlation ID across async tasks
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

# Regex patterns for sensitive PII and secrets
PAN_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SECRET_PATTERN = re.compile(
    r"\b(?:Bearer\s+[A-Za-z0-9\-._~+/]+=*|sk-[A-Za-z0-9]{20,})\b", re.IGNORECASE
)


def sanitize_pii(val: Any) -> Any:
    """Recursively redacts credit card numbers (PANs) and sensitive tokens from log content."""
    if isinstance(val, str):
        sanitized = PAN_PATTERN.sub("[REDACTED_PAN]", val)
        sanitized = SECRET_PATTERN.sub("[REDACTED_SECRET]", sanitized)
        return sanitized
    elif isinstance(val, dict):
        return {k: sanitize_pii(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_pii(item) for item in val]
    return val


class JSONFormatter(logging.Formatter):
    """Custom formatter outputting logs as structured JSON with automatic PII sanitization."""

    def format(self, record: logging.LogRecord) -> str:
        clean_msg = sanitize_pii(record.getMessage())
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": clean_msg,
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get(),
        }

        if record.exc_info:
            log_payload["exception"] = sanitize_pii(self.formatException(record.exc_info))

        # Include custom extra fields if attached
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            } and not key.startswith("_"):
                log_payload[key] = sanitize_pii(value)

        return json.dumps(log_payload, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root logger with JSONFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
