"""Nightly batch runner that isolates each target in a fresh subprocess."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from collections.abc import Mapping

logger = logging.getLogger(__name__)

TARGETS: tuple[Mapping[str, str], ...] = (
    {"source": "municipal_edogawa", "pref": "tokyo", "city": "edogawa"},
    {"source": "municipal_koto", "pref": "tokyo", "city": "koto"},
    {"source": "municipal_sumida", "pref": "tokyo", "city": "sumida"},
    {
        "source": "municipal_tokyo_metropolitan",
        "pref": "tokyo",
        "city": "tokyo-metropolitan",
    },
)

ASYNC_TIMEOUT = 300.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nightly ingest pipeline")
    parser.add_argument(
        "--worker-index",
        type=int,
        help="Index of the target to process (worker mode)",
    )
    return parser.parse_args()


def run_worker(worker_index: int) -> int:
    from dotenv import load_dotenv

    load_dotenv()

    import asyncio

    from app.db import configure_engine

    from .fetch_http import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
    from .pipeline import run_batch

    if worker_index < 0 or worker_index >= len(TARGETS):
        msg = f"worker_index must be between 0 and {len(TARGETS) - 1}"
        raise ValueError(msg)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configure_engine(db_url)

    target = TARGETS[worker_index]
    source = target["source"]
    logger.info("--- Worker started for %s (index=%s) ---", source, worker_index)

    try:
        asyncio.run(
            run_batch(
                source=source,
                pref=target["pref"],
                city=target["city"],
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
        )
        logger.info("--- Worker finished for %s ---", source)
        return 0
    except Exception:
        logger.exception("--- Worker FAILED for %s ---", source)
        return 1


def run_orchestrator() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    had_failures = False

    for index, target in enumerate(TARGETS):
        logger.info("Spawning worker index=%s for target=%s", index, target["source"])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.ingest.run_nightly",
                "--worker-index",
                str(index),
            ],
            check=False,
        )

        if result.returncode != 0:
            logger.error(
                "Worker index=%s (target=%s) failed with exit code %s",
                index,
                target["source"],
                result.returncode,
            )
            had_failures = True
        else:
            logger.info(
                "Worker index=%s (target=%s) completed successfully",
                index,
                target["source"],
            )

    # Run geocoding for missing coordinates
    # logger.info("Starting geocoding for candidates...")
    # geocode_candidates = subprocess.run(
    #     [
    #         sys.executable,
    #         "-m",
    #         "scripts.tools.geocode_missing",
    #         "--target",
    #         "candidates",
    #         "--origin",
    #         "all",
    #     ],
    #     check=False,
    # )
    # if geocode_candidates.returncode != 0:
    #     logger.error("Geocoding for candidates failed")
    #     had_failures = True

    # logger.info("Starting geocoding for gyms...")
    # geocode_gyms = subprocess.run(
    #     [
    #         sys.executable,
    #         "-m",
    #         "scripts.tools.geocode_missing",
    #         "--target",
    #         "gyms",
    #         "--origin",
    #         "scraped",
    #     ],
    #     check=False,
    # )
    # if geocode_gyms.returncode != 0:
    #     logger.error("Geocoding for gyms failed")
    #     had_failures = True

    return 1 if had_failures else 0


if __name__ == "__main__":
    args = parse_args()
    if args.worker_index is None:
        raise SystemExit(run_orchestrator())

    raise SystemExit(run_worker(args.worker_index))
