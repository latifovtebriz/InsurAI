"""Structured JSON logging configuration and correlation context."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ContextVar for propagating correlation ID across async tasks
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


class JSONFormatter(logging.Formatter):
    """Custom formatter outputting logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get(),
        }

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

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
                log_payload[key] = value

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
