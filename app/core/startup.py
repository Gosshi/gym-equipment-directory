"""Startup helpers for database migrations and readiness tracking."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Final

import structlog

_MAX_ATTEMPTS: Final[int] = int(os.getenv("ALEMBIC_STARTUP_MAX_ATTEMPTS", "10"))
_RETRY_DELAY_SECONDS: Final[float] = float(os.getenv("ALEMBIC_STARTUP_RETRY_SECONDS", "2"))
_MIGRATIONS_COMPLETED: bool = False


def is_migration_completed() -> bool:
    """Return True when startup migrations have finished successfully."""

    return _MIGRATIONS_COMPLETED


def run_database_migrations() -> None:
    """Execute `alembic upgrade head` with retries on startup."""

    global _MIGRATIONS_COMPLETED
    logger = structlog.get_logger(__name__)

    if _MIGRATIONS_COMPLETED:
        logger.info("alembic_upgrade_skipped", reason="already_completed")
        return

    if os.getenv("TESTING"):
        _MIGRATIONS_COMPLETED = True
        logger.info("alembic_upgrade_skipped", reason="testing")
        return

    command = ("alembic", "upgrade", "head")
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            logger.info("alembic_upgrade_start", attempt=attempt)
            subprocess.run(command, check=True)
        except FileNotFoundError:
            logger.error("alembic_command_missing", command=" ".join(command))
            raise SystemExit(1)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - error path
            logger.error(
                "alembic_upgrade_failed",
                attempt=attempt,
                returncode=exc.returncode,
            )
        except Exception:  # pragma: no cover - unexpected error path
            logger.exception("alembic_upgrade_exception", attempt=attempt)
        else:
            _MIGRATIONS_COMPLETED = True
            logger.info("alembic_upgrade_succeeded", attempt=attempt)
            return

        if attempt < _MAX_ATTEMPTS:
            delay = _RETRY_DELAY_SECONDS * attempt
            logger.info("alembic_upgrade_retry", next_attempt=attempt + 1, delay_seconds=delay)
            time.sleep(delay)

    logger.error("alembic_upgrade_exhausted", attempts=_MAX_ATTEMPTS)
    raise SystemExit(1)


__all__ = ["is_migration_completed", "run_database_migrations"]
