from __future__ import annotations

import logging
import os
from typing import Any

import structlog


def _get_log_level() -> int:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def setup_logging() -> None:
    """Configure structlog for JSON structured logging.

    - JSON lines with ISO/UTC timestamp, level, event, and bound fields
    - Includes contextvars so request_id and others flow automatically
    - Formats exception info in JSON if exc_info is attached
    - BasicConfig uses "%(message)s" so stdlib/uvicorn messages don't wrap JSON
    """

    # 1) Route stdlib logging to print only the message, so our JSON isn't double-formatted
    logging.basicConfig(level=_get_log_level(), format="%(message)s")

    # Make uvicorn/gunicorn loggers consistent with our level
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn", "gunicorn.error"):
        try:
            logging.getLogger(name).setLevel(_get_log_level())
        except Exception:
            pass

    # 2) Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,  # exc_info=True -> JSON field
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:  # convenience
    return structlog.get_logger(*args, **kwargs)
