"""Backfill category for existing GymCandidates based on parsed_json content."""

import asyncio
import logging
import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import text

from app.db import SessionLocal, configure_engine
from app.ingest.parsers.municipal._base import classify_category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_categories():
    """Update category for all existing candidates based on their parsed_json."""
    async with SessionLocal() as session:
        # Fetch all candidates with NULL category
        result = await session.execute(
            text("""
                SELECT id, name_raw, parsed_json 
                FROM gym_candidates 
                WHERE category IS NULL
            """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} candidates with NULL category")

        updated = 0
        for row in rows:
            cid, name_raw, parsed_json = row

            # Build text to classify from
            text_content = name_raw or ""
            if parsed_json:
                text_content += " " + str(parsed_json.get("facility_name", ""))
                text_content += " " + str(parsed_json.get("page_title", ""))
                text_content += " " + " ".join(parsed_json.get("equipments_raw", []))

            category = classify_category(text_content)

            await session.execute(
                text("UPDATE gym_candidates SET category = :cat WHERE id = :id"),
                {"cat": category, "id": cid},
            )
            updated += 1

            if updated % 50 == 0:
                logger.info(f"Updated {updated}/{len(rows)}...")

        await session.commit()
        logger.info(f"Backfill complete: {updated} candidates updated")

        # Show distribution
        result = await session.execute(
            text("""
                SELECT category, count(*) as cnt
                FROM gym_candidates
                GROUP BY category
                ORDER BY cnt DESC
            """)
        )
        print("\n=== Category Distribution ===")
        for row in result:
            print(f"{row[0] or 'NULL'}: {row[1]}")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(backfill_categories())
