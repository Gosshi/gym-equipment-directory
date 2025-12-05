import argparse
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal, configure_engine
from app.models import Gym, GymCandidate
from app.models.gym_candidate import CandidateStatus
from app.services.canonical import make_canonical_id

logger = logging.getLogger(__name__)


async def revert_approvals(
    keyword: str | None,
    since_hours: int,
    status_to: str,
    dry_run: bool,
    list_all: bool = False,
) -> None:
    async with SessionLocal() as session:
        # 1. Find candidates updated recently
        since = datetime.now(UTC) - timedelta(hours=since_hours)
        stmt = select(GymCandidate).where(GymCandidate.updated_at >= since)

        if not list_all:
            stmt = stmt.where(GymCandidate.status == CandidateStatus.approved)

        if keyword:
            stmt = stmt.where(GymCandidate.name_raw.like(f"%{keyword}%"))

        stmt = stmt.order_by(GymCandidate.updated_at.desc())

        result = await session.execute(stmt)
        candidates = result.scalars().all()

        if not candidates:
            logger.info("No candidates found matching the criteria.")
            return

        if list_all:
            logger.info(
                f"Found {len(candidates)} candidates updated in the last {since_hours} hours:"
            )
            for c in candidates:
                logger.info(
                    f"  ID={c.id} Status={c.status.value} Updated={c.updated_at} Name={c.name_raw}"
                )
            return

        logger.info(f"Found {len(candidates)} candidates to revert.")

        for candidate in candidates:
            # 2. Find corresponding Gym
            # We reconstruct canonical_id to find the gym
            # Note: This logic must match ApproveService
            parsed = candidate.parsed_json or {}
            name = parsed.get("facility_name") or candidate.name_raw
            pref = candidate.pref_slug
            city = candidate.city_slug

            if not pref or not city:
                logger.warning(f"Candidate {candidate.id} missing pref/city, skipping.")
                continue

            canonical_id = make_canonical_id(pref, city, name)

            gym_stmt = select(Gym).where(Gym.canonical_id == canonical_id)
            gym_result = await session.execute(gym_stmt)
            gym = gym_result.scalar_one_or_none()

            if not gym:
                logger.warning(
                    f"Gym not found for candidate {candidate.id} "
                    f"(canonical_id={canonical_id}), skipping."
                )
                # Even if gym is not found, we might want to reset candidate status?
                # But if gym is missing, maybe it wasn't created or was already deleted.
                # Let's assume we only revert if we find the gym or if forced.
                # For safety, let's just reset status if gym is missing?
                # No, if gym is missing, maybe it was linked to an existing gym?
                # It's complex. Let's stick to "delete created gym".
                continue

            logger.info(f"Candidate {candidate.id} -> Gym {gym.id} ({gym.name})")

            if not dry_run:
                # 3. Delete Gym
                await session.delete(gym)

                # 4. Reset Candidate Status
                candidate.status = CandidateStatus(status_to)
                logger.info(
                    f"  Deleted Gym {gym.id} and set Candidate {candidate.id} to {status_to}"
                )
            else:
                logger.info(
                    f"  [Dry-Run] Would delete Gym {gym.id} "
                    f"and set Candidate {candidate.id} to {status_to}"
                )

        if not dry_run:
            await session.commit()
            logger.info("Changes committed.")
        else:
            logger.info("Dry-run complete. No changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Revert accidentally approved gyms")
    parser.add_argument("--keyword", help="Filter by name keyword (e.g. '中学校')")
    parser.add_argument("--since-hours", type=int, default=24, help="Look back hours (default: 24)")
    parser.add_argument(
        "--status-to",
        default="new",
        choices=["new", "ignored", "rejected"],
        help="Status to revert to (default: new)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False, help="Dry run (no changes)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute changes (opposite of dry-run, for safety)",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all updated candidates regardless of status (debug)",
    )

    args = parser.parse_args()

    # Default to dry-run unless --execute is passed
    dry_run = not args.execute
    if args.dry_run:
        dry_run = True

    logging.basicConfig(level=logging.INFO)

    # Load env for DB
    import os

    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configure_engine(db_url)
    else:
        logger.warning("DATABASE_URL is not set. Connecting to default (likely empty/local) DB.")

    asyncio.run(
        revert_approvals(args.keyword, args.since_hours, args.status_to, dry_run, args.list_all)
    )


if __name__ == "__main__":
    main()
