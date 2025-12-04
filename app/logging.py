from __future__ import annotations

import logging
import os
from typing import Any

import structlog


def _get_log_level() -> int:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def setup_logging(log_file: str | os.PathLike | None = None) -> None:
    """Configure structlog for JSON structured logging.

    - JSON lines with ISO/UTC timestamp, level, event, and bound fields
    - Includes contextvars so request_id and others flow automatically
    - Formats exception info in JSON if exc_info is attached
    - BasicConfig uses "%(message)s" so stdlib/uvicorn messages don't wrap JSON
    """

    # Shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]

    log_format = os.getenv("LOG_FORMAT", "json").lower()
    if os.getenv("APP_ENV") == "dev" and "LOG_FORMAT" not in os.environ:
        log_format = "console"

    # Structlog configuration
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Formatter for stdlib logging
    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(str(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(str(log_file), encoding="utf-8"))

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=_get_log_level(),
        handlers=handlers,
        force=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:  # convenience
    return structlog.get_logger(*args, **kwargs)
