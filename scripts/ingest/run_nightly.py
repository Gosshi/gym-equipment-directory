"""Nightly batch runner that isolates each target in a fresh subprocess."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# Schedule definition: Day of week (0=Mon, 6=Sun) -> List of targets
# Note: Tokyo Metropolitan is assigned to Monday
SCHEDULE: dict[str, tuple[Mapping[str, str], ...]] = {
    "mon": (
        {"source": "municipal_chiyoda", "pref": "tokyo", "city": "chiyoda"},
        {"source": "municipal_chuo", "pref": "tokyo", "city": "chuo"},
        {"source": "municipal_minato", "pref": "tokyo", "city": "minato"},
        {
            "source": "municipal_tokyo_metropolitan",
            "pref": "tokyo",
            "city": "tokyo-metropolitan",
        },
        {"source": "municipal_shinjuku", "pref": "tokyo", "city": "shinjuku"},
        {"source": "municipal_bunkyo", "pref": "tokyo", "city": "bunkyo"},
        {"source": "municipal_taito", "pref": "tokyo", "city": "taito"},
        {"source": "municipal_sumida", "pref": "tokyo", "city": "sumida"},
        {"source": "municipal_koto", "pref": "tokyo", "city": "koto"},
        {"source": "municipal_shinagawa", "pref": "tokyo", "city": "shinagawa"},
        {"source": "municipal_meguro", "pref": "tokyo", "city": "meguro"},
        {"source": "municipal_ota", "pref": "tokyo", "city": "ota"},
    ),
    "fri": (
        {"source": "municipal_setagaya", "pref": "tokyo", "city": "setagaya"},
        {"source": "municipal_shibuya", "pref": "tokyo", "city": "shibuya"},
        {"source": "municipal_nakano", "pref": "tokyo", "city": "nakano"},
        {"source": "municipal_suginami", "pref": "tokyo", "city": "suginami"},
        {"source": "municipal_toshima", "pref": "tokyo", "city": "toshima"},
        {"source": "municipal_kita", "pref": "tokyo", "city": "kita"},
        {"source": "municipal_arakawa", "pref": "tokyo", "city": "arakawa"},
        {"source": "municipal_itabashi", "pref": "tokyo", "city": "itabashi"},
        {"source": "municipal_nerima", "pref": "tokyo", "city": "nerima"},
        {"source": "municipal_adachi", "pref": "tokyo", "city": "adachi"},
        {"source": "municipal_katsushika", "pref": "tokyo", "city": "katsushika"},
        {"source": "municipal_edogawa", "pref": "tokyo", "city": "edogawa"},
    ),
}

ASYNC_TIMEOUT = 300.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nightly ingest pipeline")
    parser.add_argument(
        "--worker-index",
        type=int,
        help="Index of the target to process (worker mode)",
    )
    parser.add_argument(
        "--day",
        type=str,
        choices=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        help="Force run for a specific day of the week (orchestrator mode)",
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


def run_worker(worker_index: int, day_key: str) -> int:
    from dotenv import load_dotenv

    load_dotenv()

    import asyncio

    from app.db import configure_engine

    from .fetch_http import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
    from .pipeline import run_batch

    targets = SCHEDULE.get(day_key)
    if not targets:
        logger.error(f"No targets found for day: {day_key}")
        return 1

    if worker_index < 0 or worker_index >= len(targets):
        msg = f"worker_index must be between 0 and {len(targets) - 1}"
        raise ValueError(msg)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configure_engine(db_url)

    target = targets[worker_index]
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
                auto_approve=False,
            )
        )
        logger.info("--- Worker finished for %s ---", source)
        return 0
    except Exception:
        logger.exception("--- Worker FAILED for %s ---", source)
        return 1


def run_orchestrator(force_day: str | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Calculate current day in JST (UTC+9)
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    # 0=Mon, 6=Sun
    weekday_idx = now_jst.weekday()
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    current_day = days[weekday_idx]

    if force_day:
        logger.info(f"Forcing run for day: {force_day}")
        current_day = force_day
    else:
        logger.info(f"Running schedule for day: {current_day} (JST)")

    targets = SCHEDULE.get(current_day)
    if not targets:
        logger.warning(f"No targets defined for {current_day}")
        return 0

    had_failures = False

    # Run discovery for each target ward
    logger.info("Starting discovery phase...")
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if api_key and cx:
        for target in targets:
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

    # Run workers in parallel
    import concurrent.futures

    max_workers = 2  # Reduced from 5 to prevent OOM on Render Starter (512MB RAM)
    logger.info(f"Spawning workers with max_workers={max_workers}...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_target = {}
        for index, target in enumerate(targets):
            logger.info("Scheduling worker index=%s for target=%s", index, target["source"])
            future = executor.submit(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest.run_nightly",
                    "--worker-index",
                    str(index),
                    "--day",
                    current_day,
                ],
                check=False,
                capture_output=True,  # Capture output to avoid interleaving logs
                # Letting it flow is better for live logs, but might be messy.
                # Given it's a cron job, interleaved logs are okay-ish, but maybe hard to read.
                # But capturing hides progress until done.
                # Let's keep check=False and NOT capture, so logs stream (interleaved).
            )
            future_to_target[future] = (index, target)

        for future in concurrent.futures.as_completed(future_to_target):
            index, target = future_to_target[future]
            source = target["source"]
            try:
                result = future.result()
                if result.returncode != 0:
                    logger.error(
                        "Worker index=%s (target=%s) failed with exit code %s",
                        index,
                        source,
                        result.returncode,
                    )
                    had_failures = True
                else:
                    logger.info(
                        "Worker index=%s (target=%s) completed successfully",
                        index,
                        source,
                    )
            except Exception as exc:
                logger.error(
                    "Worker index=%s (target=%s) generated an exception: %s",
                    index,
                    source,
                    exc,
                )
                had_failures = True

    # Geocoding disabled by user request (manual only)
    # logger.info("Starting geocoding for candidates...")
    # ... (removed)

    # Collect summary
    summary_lines = [f"**Nightly Run Report ({current_day})**"]
    if had_failures:
        summary_lines.append("🔴 **Status:** Failed (Check logs)")
    else:
        summary_lines.append("🟢 **Status:** Success")

    summary_lines.append(f"\n**Targets:** {len(targets)}")

    # TODO: We should collect actual metrics from workers/discovery,
    # but for now we just report success/failure of the process.
    # To do this properly, we might need to parse logs or have workers write to a status file/DB.
    # For this iteration, simple process status is enough.

    # Run backfill of tags to fix any missing tags in existing candidates
    try:
        logger.info("Starting backfill of candidate tags...")
        # Import dynamically to avoid circular imports if any
        import asyncio

        from scripts.backfill_candidate_tags import backfill_tags

        asyncio.run(backfill_tags())
        logger.info("Backfill completed.")
        summary_lines.append("\n**Backfill:** Completed")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        summary_lines.append(f"\n**Backfill:** Failed ({e})")

    message = "\n".join(summary_lines)

    # Send notification
    try:
        import asyncio

        from app.services.notification import send_notification

        asyncio.run(send_notification(message))
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

    return 1 if had_failures else 0


if __name__ == "__main__":
    args = parse_args()
    if args.discovery_ward:
        raise SystemExit(run_discovery_worker(args.discovery_ward))

    if args.worker_index is None:
        raise SystemExit(run_orchestrator(force_day=args.day))

    # Worker mode needs to know which day's schedule to use to look up the target by index
    # But wait, worker_index relies on the TARGETS list which is now dynamic.
    # We must pass the day to the worker as well.
    if not args.day:
        # If day is not passed to worker, it cannot know which list to use.
        # We need to calculate it again or require it.
        # Calculating it again is risky if the day changes mid-run
        # (rare but possible around midnight).
        # Better to require it or default to current day.
        jst = timezone(timedelta(hours=9))
        weekday_idx = datetime.now(jst).weekday()
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        args.day = days[weekday_idx]

    raise SystemExit(run_worker(args.worker_index, args.day))
