import asyncio
import logging
import os

from sqlalchemy import delete, text, update

from app.db import SessionLocal, configure_engine
from app.models import Gym, GymCandidate
from app.models.gym_candidate import CandidateStatus

logger = logging.getLogger(__name__)


async def reset_data(execute: bool) -> None:
    async with SessionLocal() as session:
        # 1. Count current data
        gym_count = await session.scalar(text("SELECT count(*) FROM gyms"))
        cand_count = await session.scalar(text("SELECT count(*) FROM gym_candidates"))

        logger.info(f"Current Status: Gyms={gym_count}, Candidates={cand_count}")

        if not execute:
            logger.info("[Dry-Run] Would delete all Gyms and set all Candidates to 'reviewing'.")
            logger.info("Run with --execute to apply changes.")
            return

        # 2. Delete all Gyms
        # Note: GymEquipment should cascade delete, but we can delete explicitly if needed.
        # Let's rely on cascade or delete explicitly to be safe/clear.
        logger.info("Deleting all Gyms...")
        await session.execute(delete(Gym))

        # 3. Update all Candidates to 'reviewing'
        logger.info("Updating all Candidates to 'reviewing'...")
        await session.execute(update(GymCandidate).values(status=CandidateStatus.reviewing))

        await session.commit()

        # 4. Verify
        gym_count_after = await session.scalar(text("SELECT count(*) FROM gyms"))
        cand_count_after = await session.scalar(text("SELECT count(*) FROM gym_candidates"))
        logger.info(f"Done. Gyms={gym_count_after}, Candidates={cand_count_after}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reset all data: Delete Gyms, Reset Candidates")
    parser.add_argument("--execute", action="store_true", help="Execute changes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv

    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL is not set.")
        return

    configure_engine(db_url)

    asyncio.run(reset_data(args.execute))


if __name__ == "__main__":
    main()
