"""Nightly batch runner that isolates each target in a fresh subprocess."""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime

logger = logging.getLogger(__name__)


# Schedule definition: Master Data for Ward Configurations
# Used to look up configuration by city name.
SCHEDULE: dict[str, tuple[Mapping[str, str], ...]] = {
    "mon": (
        {"source": "municipal_chiyoda", "pref": "tokyo", "city": "chiyoda"},
        {"source": "municipal_chuo", "pref": "tokyo", "city": "chuo"},
        {"source": "municipal_minato", "pref": "tokyo", "city": "minato"},
        {"source": "municipal_shinjuku", "pref": "tokyo", "city": "shinjuku"},
        {"source": "municipal_bunkyo", "pref": "tokyo", "city": "bunkyo"},
        {"source": "municipal_taito", "pref": "tokyo", "city": "taito"},
        {"source": "municipal_sumida", "pref": "tokyo", "city": "sumida"},
        {"source": "municipal_koto", "pref": "tokyo", "city": "koto"},
    ),
    "tue": (
        {"source": "municipal_shinagawa", "pref": "tokyo", "city": "shinagawa"},
        {"source": "municipal_meguro", "pref": "tokyo", "city": "meguro"},
        {"source": "municipal_ota", "pref": "tokyo", "city": "ota"},
        {"source": "municipal_setagaya", "pref": "tokyo", "city": "setagaya"},
        {"source": "municipal_shibuya", "pref": "tokyo", "city": "shibuya"},
        {"source": "municipal_nakano", "pref": "tokyo", "city": "nakano"},
        {"source": "municipal_suginami", "pref": "tokyo", "city": "suginami"},
        {"source": "municipal_toshima", "pref": "tokyo", "city": "toshima"},
    ),
    "wed": (
        {"source": "municipal_kita", "pref": "tokyo", "city": "kita"},
        {"source": "municipal_arakawa", "pref": "tokyo", "city": "arakawa"},
        {"source": "municipal_itabashi", "pref": "tokyo", "city": "itabashi"},
        {"source": "municipal_nerima", "pref": "tokyo", "city": "nerima"},
        {"source": "municipal_adachi", "pref": "tokyo", "city": "adachi"},
        {"source": "municipal_katsushika", "pref": "tokyo", "city": "katsushika"},
        {"source": "municipal_edogawa", "pref": "tokyo", "city": "edogawa"},
        {
            "source": "municipal_tokyo_metropolitan",
            "pref": "tokyo",
            "city": "tokyo-metropolitan",
        },
    ),
}

# Flatten SCHEDULE to create a Master Lookup Dict: city -> config
WARD_CONFIGS: dict[str, dict[str, str]] = {}
for batch in SCHEDULE.values():
    for target in batch:
        WARD_CONFIGS[target["city"]] = target

ASYNC_TIMEOUT = 300.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nightly ingest pipeline")
    parser.add_argument(
        "--worker-target",
        type=str,
        help="City name of the target to process (worker mode)",
    )
    # Kept for backward compatibility if needed, but primary mode is now ENV based
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


def run_worker(target_city: str) -> int:
    from dotenv import load_dotenv

    load_dotenv()

    import asyncio

    from app.db import configure_engine

    from .fetch_http import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
    from .pipeline import run_batch

    target = WARD_CONFIGS.get(target_city)
    if not target:
        logger.error(f"No configuration found for city: {target_city}")
        return 1

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configure_engine(db_url)

    source = target["source"]
    logger.info("--- Worker started for %s (city=%s) ---", source, target_city)

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
                auto_approve=False,
            )
        )
        logger.info("--- Worker finished for %s ---", source)
        return 0
    except Exception:
        logger.exception("--- Worker FAILED for %s ---", source)
        return 1


async def run_orchestrator() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # 1. Check Payload (Environment Variable)
    target_wards_str = os.getenv("TARGET_WARDS", "").strip()
    if not target_wards_str:
        logger.info("TARGET_WARDS env var is empty. Exiting without action.")
        return 0

    target_cities = [w.strip() for w in target_wards_str.split(",") if w.strip()]
    if not target_cities:
        logger.info("No valid wards found in TARGET_WARDS. Exiting.")
        return 0

    logger.info(f"Manual Execution Started. Targets: {target_cities}")

    # Validate targets
    valid_configs = []
    for city in target_cities:
        if city in WARD_CONFIGS:
            valid_configs.append(WARD_CONFIGS[city])
        else:
            logger.warning(f"Skipping unknown city: {city}")

    if not valid_configs:
        logger.error("No valid configurations found for requested wards.")
        return 0

    had_failures = False

    # 2. Run Discovery (Sequential / Parallel)
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if api_key and cx:
        logger.info("Starting discovery phase...")
        for target in valid_configs:
            # Skip if not a municipal target
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

    # 3. Run Workers (Parallel)
    max_workers = 2
    logger.info(f"Spawning workers with max_workers={max_workers}...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_city = {}
        for target in valid_configs:
            city = target["city"]
            logger.info(f"Scheduling worker for {city}...")
            future = executor.submit(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest.run_nightly",
                    "--worker-target",
                    city,
                ],
                check=False,
                capture_output=False,
            )
            future_to_city[future] = city

        for future in concurrent.futures.as_completed(future_to_city):
            city = future_to_city[future]
            try:
                result = future.result()
                if result.returncode != 0:
                    # Log as warning to avoid double-error log confusion,
                    # since worker already logged the exception.
                    logger.warning(
                        "Worker for city=%s failed with exit code %s",
                        city,
                        result.returncode,
                    )
                    had_failures = True
                else:
                    logger.info(
                        "Worker for city=%s completed successfully",
                        city,
                    )
            except Exception as exc:
                logger.error(
                    "Worker execution for city=%s generated an exception: %s",
                    city,
                    exc,
                )
                had_failures = True

    # 4. Cleanup & Summary
    summary_lines = ["**Manual Run Report**"]
    summary_lines.append(f"Targets: {', '.join(target_cities)}")
    if had_failures:
        summary_lines.append("🔴 **Status:** Failed (Check logs)")
    else:
        summary_lines.append("🟢 **Status:** Success")

    # Run backfill of tags
    try:
        logger.info("Starting backfill of candidate tags...")
        from scripts.backfill_candidate_tags import backfill_tags

        # Process recent entries (default behavior or adjusted if needed)
        await backfill_tags()

        logger.info("Backfill completed.")
        summary_lines.append("\n**Backfill:** Completed")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        summary_lines.append(f"\n**Backfill:** Failed ({e})")

    # Deduplication
    try:
        logger.info("Starting candidate deduplication...")
        from scripts.deduplicate_candidates import deduplicate_candidates

        await deduplicate_candidates()

        logger.info("Deduplication completed.")
        summary_lines.append("\n**Deduplication:** Completed")
    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        summary_lines.append(f"\n**Deduplication:** Failed ({e})")

    # Auto-Approval
    try:
        logger.info("Starting candidate auto-approval...")
        from scripts.auto_approve_candidates import auto_approve_candidates

        stats = await auto_approve_candidates(dry_run=True)

        merged = stats.get("merged", 0)
        approved = stats.get("approved", 0)
        skipped = stats.get("skipped", 0)

        logger.info("Auto-approval completed.")
        summary_lines.append(
            f"\n**Auto-Approval:** Completed "
            f"(Merged={merged}, Approved={approved}, Skipped={skipped})"
        )
    except Exception as e:
        logger.error(f"Auto-approval failed: {e}")
        summary_lines.append(f"\n**Auto-Approval:** Failed ({e})")

    # Send notification
    try:
        from app.services.notification import send_notification

        await send_notification("\n".join(summary_lines))

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

    # clean up engine
    from app.db import engine

    await engine.dispose()

    return 1 if had_failures else 0


if __name__ == "__main__":
    args = parse_args()
    if args.discovery_ward:
        raise SystemExit(run_discovery_worker(args.discovery_ward))

    if args.worker_target:
        raise SystemExit(run_worker(args.worker_target))
    else:
        # Orchestrator
        import asyncio

        raise SystemExit(asyncio.run(run_orchestrator()))
