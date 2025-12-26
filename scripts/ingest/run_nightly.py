"""Nightly batch runner that isolates each target in a fresh subprocess."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# Schedule definition: Day of week (0=Mon, 6=Sun) -> List of targets
# Note: Tokyo Metropolitan is assigned to Monday
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
    "wed": (
        {"source": "municipal_shinagawa", "pref": "tokyo", "city": "shinagawa"},
        {"source": "municipal_meguro", "pref": "tokyo", "city": "meguro"},
        {"source": "municipal_ota", "pref": "tokyo", "city": "ota"},
        {"source": "municipal_setagaya", "pref": "tokyo", "city": "setagaya"},
        {"source": "municipal_shibuya", "pref": "tokyo", "city": "shibuya"},
        {"source": "municipal_nakano", "pref": "tokyo", "city": "nakano"},
        {"source": "municipal_suginami", "pref": "tokyo", "city": "suginami"},
        {"source": "municipal_toshima", "pref": "tokyo", "city": "toshima"},
    ),
    "fri": (
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


async def run_orchestrator(force_day: str | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Calculate current day in JST (UTC+9)
    # jst = timezone(timedelta(hours=9))  <-- unused

    current_day = "accelerated"  # Dummy value for logging

    # --- TEMPORARY ACCELERATED SCHEDULE (User Request) ---
    # Run all 23 wards in 6 batches (every 4 hours)
    # Flatten all targets
    ALL_TARGETS = []
    for day_targets in SCHEDULE.values():
        ALL_TARGETS.extend(day_targets)

    # Sort to ensure deterministic order (by city code or name)
    ALL_TARGETS.sort(key=lambda x: x["city"])

    current_hour = datetime.now(UTC).hour
    # Runs at 0, 4, 8, 12, 16, 20 UTC
    # 0 -> Batch 0
    # 4 -> Batch 1
    # ...
    # 20 -> Batch 5
    batch_index = current_hour // 4

    # 23 wards / 6 batches = ~4 wards per batch
    BATCH_SIZE = 4
    start_idx = batch_index * BATCH_SIZE
    end_idx = start_idx + BATCH_SIZE

    # Handle overflow
    if start_idx >= len(ALL_TARGETS):
        # Should not happen if cron is correct, but safe fallback
        logger.info(f"Batch index {batch_index} out of range (Completed?)")
        targets = ()
    else:
        targets = tuple(ALL_TARGETS[start_idx:end_idx])

    logger.info(f"--- ACCELERATED RUN (UTC Hour: {current_hour}) ---")
    logger.info(f"Batch {batch_index + 1}/6: Processing {len(targets)} targets")

    if not targets:
        logger.info("No targets for today/time.")
        return 0

    # Regular logic follows... (spawning workers)
    had_failures = False

    # Run discovery for each target ward
    logger.info("Starting discovery phase...")
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if api_key and cx:
        for target in targets:
            # Skip if not a municipal target
            if "municipal" not in target["source"]:
                continue

            ward = target.get("city")
            if not ward or ward == "tokyo-metropolitan":
                continue

            logger.info(f"Discovering URLs for {ward}...")
            # Run discovery in SUBPROCESS to avoid async loop conflict/pollution
            # Discovery uses its own asyncio.run internally if called as script
            # Keep it as subprocess for isolation
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

    # Run workers in parallel (Subprocesses)
    import concurrent.futures

    max_workers = 2
    logger.info(f"Spawning workers with max_workers={max_workers}...")

    # Workers are also subprocesses, so they don't share our event loop
    # Reverse lookup map for worker arguments to handle accelerated batches
    # (pref, city) -> (day, index)
    target_lookup = {}
    for d, t_list in SCHEDULE.items():
        for idx, t in enumerate(t_list):
            key = (t["pref"], t["city"])
            target_lookup[key] = (d, idx)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_target = {}
        for index, target in enumerate(targets):
            # find original args
            t_key = (target["pref"], target["city"])
            if t_key not in target_lookup:
                logger.error(f"Target {t_key} not found in SCHEDULE")
                continue

            orig_day, orig_idx = target_lookup[t_key]

            logger.info(
                "Scheduling worker for %s (Original Day: %s, Idx: %s)",
                target["source"],
                orig_day,
                orig_idx,
            )
            future = executor.submit(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest.run_nightly",
                    "--worker-index",
                    str(orig_idx),
                    "--day",
                    orig_day,
                ],
                check=False,
                capture_output=False,
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

    # Collect summary
    summary_lines = [f"**Nightly Run Report ({current_day})**"]
    if had_failures:
        summary_lines.append("🔴 **Status:** Failed (Check logs)")
    else:
        summary_lines.append("🟢 **Status:** Success")

    summary_lines.append(f"\n**Targets:** {len(targets)}")

    # Run backfill of tags (Avoid nested asyncio.run)
    try:
        logger.info("Starting backfill of candidate tags...")
        from scripts.backfill_candidate_tags import backfill_tags

        # Await directly
        await backfill_tags()

        logger.info("Backfill completed.")
        summary_lines.append("\n**Backfill:** Completed")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        summary_lines.append(f"\n**Backfill:** Failed ({e})")

    # Deduplication (Avoid nested asyncio.run)
    try:
        logger.info("Starting candidate deduplication...")
        from scripts.deduplicate_candidates import deduplicate_candidates

        # Await directly
        await deduplicate_candidates()

        logger.info("Deduplication completed.")
        summary_lines.append("\n**Deduplication:** Completed")
    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        summary_lines.append(f"\n**Deduplication:** Failed ({e})")

    # Auto-Approval (New Step)
    try:
        logger.info("Starting candidate auto-approval...")
        from scripts.auto_approve_candidates import auto_approve_candidates

        # Await directly (dry_run=False to apply changes)
        stats = await auto_approve_candidates(dry_run=False)

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

    # Cost Report (New Step)
    try:
        from scripts.check_budget import get_cost_report

        cost_report = await get_cost_report(days=1)
        summary_lines.append(f"\n{cost_report}")
    except Exception as e:
        logger.error(f"Cost report generation failed: {e}")
        summary_lines.append(f"\n**Cost Report:** Failed ({e})")

    message = "\n".join(summary_lines)

    # Send notification (Avoid nested asyncio.run)
    try:
        from app.services.notification import send_notification

        # Await directly
        await send_notification(message)

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

    # Dispose of the engine to close all connections cleanly
    from app.db import engine

    await engine.dispose()

    return 1 if had_failures else 0


if __name__ == "__main__":
    args = parse_args()
    if args.discovery_ward:
        # Discovery worker uses its own asyncio.run inside
        raise SystemExit(run_discovery_worker(args.discovery_ward))

    if args.worker_index is None:
        # Orchestrator is now async
        import asyncio

        raise SystemExit(asyncio.run(run_orchestrator(force_day=args.day)))
    else:
        # Worker is sync wrapper around async run_batch (inside run_worker)
        # run_worker uses asyncio.run internally, which is fine as it is a separate process
        raise SystemExit(run_worker(args.worker_index, args.day))
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
