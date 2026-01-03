"""Backfill gym_id for approved candidates.

Matches approved candidates with their corresponding gyms using:
1. official_url exact match
2. name + pref_slug + city_slug fuzzy match
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.gym import Gym
from app.models.gym_candidate import CandidateStatus, GymCandidate

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill gym_id for approved candidates")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without applying updates",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logs per record",
    )
    return parser


async def _backfill(
    session: AsyncSession,
    dry_run: bool,
    verbose: bool,
) -> dict[str, int]:
    """Backfill gym_id for approved candidates."""
    # Get approved candidates without gym_id
    stmt = (
        select(GymCandidate)
        .where(GymCandidate.status == CandidateStatus.approved)
        .where(GymCandidate.gym_id.is_(None))
        .order_by(GymCandidate.id)
    )
    result = await session.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates:
        logger.info("No approved candidates without gym_id")
        return {"total": 0, "matched": 0, "unmatched": 0}

    logger.info("Found %d approved candidates without gym_id", len(candidates))

    matched = 0
    unmatched = 0

    for candidate in candidates:
        gym_id: int | None = None

        # Method 1: Match by official_url
        official_url = (candidate.parsed_json or {}).get("official_url")
        if official_url:
            gym_stmt = select(Gym.id).where(Gym.official_url == official_url).limit(1)
            gym_id = await session.scalar(gym_stmt)
            if gym_id:
                if verbose:
                    logger.info(
                        "Matched candidate %d by official_url: %s -> gym %d",
                        candidate.id,
                        official_url,
                        gym_id,
                    )

        # Method 2: Match by name + location (fuzzy)
        if gym_id is None and candidate.name_raw and candidate.pref_slug and candidate.city_slug:
            # Try exact name match first
            gym_stmt = (
                select(Gym.id)
                .where(Gym.name == candidate.name_raw)
                .where(Gym.pref == candidate.pref_slug)
                .where(Gym.city == candidate.city_slug)
                .limit(1)
            )
            gym_id = await session.scalar(gym_stmt)
            if gym_id and verbose:
                logger.info(
                    "Matched candidate %d by name+location: %s -> gym %d",
                    candidate.id,
                    candidate.name_raw,
                    gym_id,
                )

        if gym_id:
            matched += 1
            if not dry_run:
                # Update candidate gym_id
                update_stmt = (
                    update(GymCandidate)
                    .where(GymCandidate.id == candidate.id)
                    .values(gym_id=gym_id)
                )
                await session.execute(update_stmt)
        else:
            unmatched += 1
            if verbose:
                logger.warning(
                    "Could not match candidate %d: %s (pref=%s, city=%s, official_url=%s)",
                    candidate.id,
                    candidate.name_raw,
                    candidate.pref_slug,
                    candidate.city_slug,
                    official_url,
                )

    if not dry_run:
        await session.commit()

    return {
        "total": len(candidates),
        "matched": matched,
        "unmatched": unmatched,
    }


async def backfill_candidate_gym_id(
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, int]:
    """Backfill gym_id for approved candidates."""
    async with SessionLocal() as session:
        return await _backfill(session, dry_run, verbose)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args(argv)

    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info("Starting gym_id backfill (%s)", mode)

    try:
        summary = asyncio.run(
            backfill_candidate_gym_id(
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        )
    except Exception:
        logger.exception("Backfill script failed")
        return 1

    logger.info(
        "Summary: total=%d, matched=%d, unmatched=%d",
        summary["total"],
        summary["matched"],
        summary["unmatched"],
    )

    if args.dry_run:
        logger.info("This was a dry run. No changes were made.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
