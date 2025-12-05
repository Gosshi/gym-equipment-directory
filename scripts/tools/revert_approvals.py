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
    target_status: str = "approved",
    mode: str = "candidates",
) -> None:
    async with SessionLocal() as session:
        since = datetime.now(UTC) - timedelta(hours=since_hours)

        if mode == "gyms":
            # Search Gyms directly
            stmt = select(Gym).where(Gym.created_at >= since)
            if keyword:
                stmt = stmt.where(Gym.name.like(f"%{keyword}%"))

            stmt = stmt.order_by(Gym.created_at.desc())
            result = await session.execute(stmt)
            gyms = result.scalars().all()

            if not gyms:
                logger.info("No gyms found matching the criteria.")
                return

            logger.info(f"Found {len(gyms)} gyms created in the last {since_hours} hours.")

            for gym in gyms:
                logger.info(f"Gym {gym.id} ({gym.name}) Created={gym.created_at}")

                # Try to find associated candidate to reset
                # This is a best-effort reverse lookup
                # cand_stmt = select(GymCandidate).where(
                #     GymCandidate.parsed_json['approved_gym_slug'].astext == gym.slug
                # )
                # Or by canonical_id if available
                # (GymCandidate doesn't store it directly usually, but we can try)
                # Actually, GymCandidate doesn't link back easily unless we use
                # the same canonical_id logic.
                # Let's try to find candidates that *would* generate this gym.
                # This is hard.
                # Alternative: Find candidates with same name/pref/city

                # For now, just delete the Gym is the priority.
                # Alternative: Find candidates with same name/pref/city

                # For now, just delete the Gym is the priority.

                if not dry_run:
                    await session.delete(gym)
                    logger.info(f"  Deleted Gym {gym.id}")
                else:
                    logger.info(f"  [Dry-Run] Would delete Gym {gym.id}")

            if not dry_run:
                await session.commit()
                logger.info("Changes committed.")
            else:
                logger.info("Dry-run complete. No changes made.")
            return

        # Original Candidate-based logic
        # 1. Find candidates updated recently
        stmt = select(GymCandidate).where(GymCandidate.updated_at >= since)

        if not list_all:
            stmt = stmt.where(GymCandidate.status == CandidateStatus(target_status))

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

        logger.info(f"Found {len(candidates)} candidates to process (Target: {target_status}).")

        for candidate in candidates:
            # 2. Find corresponding Gym
            # Always try to find gym if we are cleaning up, regardless of status
            gym = None
            parsed = candidate.parsed_json or {}
            name = parsed.get("facility_name") or candidate.name_raw
            pref = candidate.pref_slug
            city = candidate.city_slug

            if pref and city:
                canonical_id = make_canonical_id(pref, city, name)
                gym_stmt = select(Gym).where(Gym.canonical_id == canonical_id)
                gym_result = await session.execute(gym_stmt)
                gym = gym_result.scalar_one_or_none()

            if gym:
                logger.info(f"Candidate {candidate.id} -> Gym {gym.id} ({gym.name})")
            else:
                logger.info(
                    f"Candidate {candidate.id} ({candidate.name_raw}) "
                    "-> No Gym found (or not searching)"
                )

            if not dry_run:
                # 3. Delete Gym if exists
                if gym:
                    await session.delete(gym)
                    logger.info(f"  Deleted Gym {gym.id}")

                # 4. Reset Candidate Status
                candidate.status = CandidateStatus(status_to)
                logger.info(f"  Set Candidate {candidate.id} to {status_to}")
            else:
                msg = f"  [Dry-Run] Would set Candidate {candidate.id} to {status_to}"
                if gym:
                    msg += f" and delete Gym {gym.id}"
                logger.info(msg)

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
        "--target-status",
        default="approved",
        choices=["new", "reviewing", "approved", "rejected", "ignored"],
        help="Target status to process (default: approved)",
    )
    parser.add_argument(
        "--mode",
        default="candidates",
        choices=["candidates", "gyms"],
        help="Search mode: 'candidates' (default) or 'gyms' (direct Gym table search)",
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
        revert_approvals(
            args.keyword,
            args.since_hours,
            args.status_to,
            dry_run,
            args.list_all,
            args.target_status,
            args.mode,
        )
    )


if __name__ == "__main__":
    main()
