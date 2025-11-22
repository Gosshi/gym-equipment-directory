"""Nightly batch runner for municipal ingest pipelines."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Mapping

from dotenv import load_dotenv

from app.db import configure_engine

from .fetch_http import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
from .pipeline import run_batch

logger = logging.getLogger(__name__)

TARGETS: tuple[Mapping[str, str], ...] = (
    {"source": "municipal_edogawa", "pref": "tokyo", "city": "edogawa-ku"},
    {"source": "municipal_koto", "pref": "tokyo", "city": "koto-ku"},
    {"source": "municipal_sumida", "pref": "tokyo", "city": "sumida-ku"},
    {"source": "municipal_tokyo_metropolitan", "pref": "tokyo", "city": "shinjuku-ku"},
)


ASYNC_TIMEOUT = 180.0


async def _run_target(target: Mapping[str, str]) -> bool:
    source = target["source"]
    pref = target["pref"]
    city = target["city"]
    log_extra = {"source": source, "pref": pref, "city": city}
    logger.info("Starting nightly ingest", extra=log_extra)
    try:
        await run_batch(
            source=source,
            pref=pref,
            city=city,
            limit=None,
            dry_run=False,
            max_retries=None,
            timeout=ASYNC_TIMEOUT,
            min_delay=DEFAULT_MIN_DELAY,
            max_delay=DEFAULT_MAX_DELAY,
            respect_robots=True,
            user_agent=DEFAULT_USER_AGENT,
            force=False,
        )
    except Exception:
        logger.exception("Nightly ingest failed for source", extra=log_extra)
        return False

    logger.info("Nightly ingest completed", extra=log_extra)
    return True


async def run_all_targets() -> int:
    had_failures = False
    for target in TARGETS:
        success = await _run_target(target)
        if not success:
            had_failures = True
    return 1 if had_failures else 0


def main() -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    configure_engine(os.getenv("DATABASE_URL"))
    return asyncio.run(run_all_targets())


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
