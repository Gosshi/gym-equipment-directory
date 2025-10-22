"""Startup helpers for database migrations and readiness tracking."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Final

import structlog
from structlog.stdlib import BoundLogger

_MAX_ATTEMPTS: Final[int] = int(os.getenv("ALEMBIC_STARTUP_MAX_ATTEMPTS", "10"))
_RETRY_DELAY_SECONDS: Final[float] = float(os.getenv("ALEMBIC_STARTUP_RETRY_SECONDS", "2"))
_MIGRATIONS_COMPLETED: bool = False
_MIGRATION_ERROR: str | None = None
_WORKER: threading.Thread | None = None


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


def _determine_exit_policy() -> bool:
    override = os.getenv("ALEMBIC_EXIT_ON_FAILURE")
    if override is not None:
        return _truthy(override)
    return os.getenv("APP_ENV", "dev").lower() == "prod"


_EXIT_ON_FAILURE: Final[bool] = _determine_exit_policy()


def is_migration_completed() -> bool:
    """Return True when startup migrations have finished successfully."""

    return _MIGRATIONS_COMPLETED


def last_migration_error() -> str | None:
    """Return the most recent migration error message if available."""

    return _MIGRATION_ERROR


def run_database_migrations() -> None:
    """Execute `alembic upgrade head` with retries on startup."""

    global _MIGRATIONS_COMPLETED, _MIGRATION_ERROR, _WORKER
    logger = structlog.get_logger(__name__)

    if _MIGRATIONS_COMPLETED:
        logger.info("alembic_upgrade_skipped", reason="already_completed")
        return

    if os.getenv("TESTING"):
        _MIGRATIONS_COMPLETED = True
        _MIGRATION_ERROR = None
        logger.info("alembic_upgrade_skipped", reason="testing")
        return

    if _EXIT_ON_FAILURE:
        success, error_message = _run_migrations_sequence(logger)
        if success:
            _MIGRATIONS_COMPLETED = True
            _MIGRATION_ERROR = None
            return
        _MIGRATION_ERROR = error_message
        raise SystemExit(1)

    if _WORKER and _WORKER.is_alive():
        logger.info("alembic_upgrade_skipped", reason="already_running")
        return

    _MIGRATIONS_COMPLETED = False
    _MIGRATION_ERROR = None
    _WORKER = threading.Thread(
        target=_run_migrations_async,
        name="alembic-startup",
        daemon=True,
    )
    _WORKER.start()
    logger.info("alembic_upgrade_background_started")


def _run_migrations_async() -> None:
    global _MIGRATIONS_COMPLETED, _MIGRATION_ERROR

    logger = structlog.get_logger(__name__).bind(mode="async")
    success, error_message = _run_migrations_sequence(logger)
    if success:
        _MIGRATIONS_COMPLETED = True
        _MIGRATION_ERROR = None
    else:
        _MIGRATIONS_COMPLETED = False
        _MIGRATION_ERROR = error_message


def _run_migrations_sequence(logger: BoundLogger) -> tuple[bool, str | None]:
    command = ("alembic", "upgrade", "head")
    last_error: str | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            logger.info("alembic_upgrade_start", attempt=attempt)
            subprocess.run(command, check=True)
        except FileNotFoundError:
            logger.error("alembic_command_missing", command=" ".join(command))
            return False, "alembic command not found"
        except subprocess.CalledProcessError as exc:  # pragma: no cover - error path
            last_error = f"alembic exited with return code {exc.returncode}"
            logger.error(
                "alembic_upgrade_failed",
                attempt=attempt,
                returncode=exc.returncode,
            )
        except Exception as exc:  # pragma: no cover - unexpected error path
            last_error = str(exc) or exc.__class__.__name__
            logger.exception("alembic_upgrade_exception", attempt=attempt)
        else:
            logger.info("alembic_upgrade_succeeded", attempt=attempt)
            return True, None

        if attempt < _MAX_ATTEMPTS:
            delay = _RETRY_DELAY_SECONDS * attempt
            logger.info("alembic_upgrade_retry", next_attempt=attempt + 1, delay_seconds=delay)
            time.sleep(delay)

    logger.error("alembic_upgrade_exhausted", attempts=_MAX_ATTEMPTS)
    return False, last_error or "alembic upgrade failed"


__all__ = ["is_migration_completed", "last_migration_error", "run_database_migrations"]
