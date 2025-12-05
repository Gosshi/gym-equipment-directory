import asyncio
import logging
import os

from sqlalchemy import text

from app.db import SessionLocal, configure_engine

logger = logging.getLogger(__name__)


async def fix_enum() -> None:
    async with SessionLocal() as session:
        # Check current values
        try:
            result = await session.execute(
                text("SELECT unnest(enum_range(NULL::candidate_status))")
            )
            current_values = result.scalars().all()
            logger.info(f"Current candidate_status values: {current_values}")

            if "ignored" in current_values:
                logger.info("'ignored' is already present.")
                return

            logger.info("Adding 'ignored' to candidate_status...")
            # We need to run this in a transaction that commits immediately
            # or outside of transaction block?
            # ALTER TYPE cannot run inside a transaction block in some cases?
            # Actually, ADD VALUE *cannot* run inside a transaction block in older Postgres,
            # but usually it's fine in newer ones unless it's being used in the same transaction.
            # However, sqlalchemy session starts a transaction.
            # Let's try executing it.

            # For enum modification, we might need autocommit isolation level or commit immediately.
            await session.execute(
                text("ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'ignored'")
            )
            await session.commit()
            logger.info("Successfully added 'ignored'.")

        except Exception as e:
            logger.error(f"Error: {e}")
            raise


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv

    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL is not set.")
        return

    configure_engine(db_url)

    asyncio.run(fix_enum())


if __name__ == "__main__":
    main()
