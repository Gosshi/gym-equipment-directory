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
    parser.add_argument(
        "--discovery-ward",
        type=str,
        help="Ward to run discovery for (discovery mode)",
    )
    return parser.parse_args()


def run_discovery_worker(ward: str) -> int:
    from dotenv import load_dotenv

    load_dotenv()

    import asyncio
    from datetime import datetime

    from sqlalchemy import select

    from app.db import SessionLocal, configure_engine
    from app.models import Source
    from app.models.source import SourceType
    from scripts.ingest.discover import discover_urls_for_ward

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configure_engine(db_url)

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not cx:
        logger.error("GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set")
        return 1

    logger.info(f"--- Discovery Worker started for {ward} ---")

    try:
        # 1. Discover URLs
        results = discover_urls_for_ward(
            ward, api_key, cx, limit=5
        )  # Limit to 5 per ward per run to save quota

        if not results:
            logger.info("No URLs found.")
            return 0

        async def _save_discovered():
            async with SessionLocal() as session:
                for item in results:
                    url = item["link"]
                    title = item["title"]

                    # Deduplication: Check if URL already exists
                    stmt = select(Source).where(Source.url == url)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.info(f"Skipping existing URL: {url}")
                        continue

                    logger.info(f"Registering new source: {url} ({title})")
                    new_source = Source(
                        url=url,
                        title=title,
                        # Using user_submission for now as 'discovered' might not exist
                        source_type=SourceType.user_submission,
                        captured_at=datetime.utcnow(),
                    )
                    session.add(new_source)
                await session.commit()

        asyncio.run(_save_discovered())
        logger.info(f"--- Discovery Worker finished for {ward} ---")
        return 0
    except Exception:
        logger.exception(f"--- Discovery Worker FAILED for {ward} ---")
        return 1


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

    # Run discovery for each target ward
    logger.info("Starting discovery phase...")
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if api_key and cx:
        for target in TARGETS:
            # Skip if not a municipal target (e.g. tokyo-metropolitan might not need discovery)
            if "municipal" not in target["source"]:
                continue

            ward = target.get("city")
            if not ward or ward == "tokyo-metropolitan":
                continue

            logger.info(f"Discovering URLs for {ward}...")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest.run_nightly",
                    "--discovery-ward",
                    ward,
                ],
                check=False,
            )
    else:
        logger.warning(
            "Skipping discovery: GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_ENGINE_ID not set"
        )

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
    logger.info("Starting geocoding for candidates...")
    geocode_candidates = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.tools.geocode_missing",
            "--target",
            "candidates",
            "--origin",
            "all",
        ],
        check=False,
    )
    if geocode_candidates.returncode != 0:
        logger.error("Geocoding for candidates failed")
        had_failures = True

    logger.info("Starting geocoding for gyms...")
    geocode_gyms = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.tools.geocode_missing",
            "--target",
            "gyms",
            "--origin",
            "scraped",
        ],
        check=False,
    )
    if geocode_gyms.returncode != 0:
        logger.error("Geocoding for gyms failed")
        had_failures = True

    return 1 if had_failures else 0


if __name__ == "__main__":
    args = parse_args()
    if args.discovery_ward:
        raise SystemExit(run_discovery_worker(args.discovery_ward))

    if args.worker_index is None:
        raise SystemExit(run_orchestrator())

    raise SystemExit(run_worker(args.worker_index))
