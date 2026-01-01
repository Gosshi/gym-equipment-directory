"""Migration script to migrate lighting from court level to individual court items.

Moves `lighting` from court level to individual court items in the courts array.

Usage:
    # Dry run (preview changes)
    DATABASE_URL="postgresql+psycopg://..." python3 scripts/migrations/migrate_court_lighting.py

    # Apply changes
    DATABASE_URL="postgresql+psycopg://..." python3 \\
        scripts/migrations/migrate_court_lighting.py --apply
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def migrate_lighting_to_courts(parsed_json: dict) -> tuple[dict, bool]:
    """Migrate lighting from court level to individual court items.

    Old format:
        {
            "court": {
                "lighting": true,
                "courts": [
                    {"court_type": "テニス", "count": 4, "surface": "砂入り人工芝"},
                    {"court_type": "バスケットボール", "count": 1, "surface": "床"}
                ]
            }
        }

    New format:
        {
                "courts": [
                    {
                        "court_type": "テニス",
                        "count": 4,
                        "surface": "砂入り人工芝",
                        "lighting": true
                    },
                    {
                        "court_type": "バスケットボール",
                        "count": 1,
                        "surface": "床",
                        "lighting": true
                    }
                ]
            }
        }
    """
    if not parsed_json:
        return parsed_json, False

    court = parsed_json.get("court")
    if not court or not isinstance(court, dict):
        return parsed_json, False

    courts = court.get("courts")
    parent_lighting = court.get("lighting")

    # Skip if no courts array or no parent lighting to migrate
    if not courts or not isinstance(courts, list) or parent_lighting is None:
        return parsed_json, False

    # Check if any court already has lighting defined - skip if so
    any_court_has_lighting = any(
        isinstance(c, dict) and c.get("lighting") is not None for c in courts
    )

    if any_court_has_lighting:
        return parsed_json, False

    # Apply parent lighting to all courts
    modified = False
    new_courts = []

    for c in courts:
        if not isinstance(c, dict):
            new_courts.append(c)
            continue

        new_court = c.copy()
        new_court["lighting"] = parent_lighting
        modified = True
        new_courts.append(new_court)

    if not modified:
        return parsed_json, False

    # Create new court object without parent lighting
    result = parsed_json.copy()
    new_court_obj = {k: v for k, v in court.items() if k != "lighting"}
    new_court_obj["courts"] = new_courts
    result["court"] = new_court_obj

    return result, True


async def main():
    dry_run = "--apply" not in sys.argv

    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    engine = create_async_engine(DATABASE_URL)

    if dry_run:
        logger.info("=== DRY RUN MODE (use --apply to actually update) ===")
    else:
        logger.info("=== APPLYING CHANGES ===")

    gym_count = 0
    candidate_count = 0

    async with engine.connect() as conn:
        # Migrate gyms
        result = await conn.execute(
            text("""
            SELECT id, slug, parsed_json 
            FROM gyms 
            WHERE parsed_json->'court'->'courts' IS NOT NULL 
              AND parsed_json->'court'->>'lighting' IS NOT NULL
        """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} gyms with court.lighting at parent level")

        for row in rows:
            gym_id, slug, parsed_json = row
            if not parsed_json:
                continue

            new_json, modified = migrate_lighting_to_courts(parsed_json)

            if modified:
                gym_count += 1
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Fixing gym {gym_id} ({slug})")

                before_dump = json.dumps(parsed_json.get("court", {}), ensure_ascii=False)[:200]
                logger.info(f"  Before: {before_dump}")

                after_dump = json.dumps(new_json.get("court", {}), ensure_ascii=False)[:200]
                logger.info(f"  After:  {after_dump}")

                if not dry_run:
                    await conn.execute(
                        text("UPDATE gyms SET parsed_json = :json WHERE id = :id"),
                        {"json": json.dumps(new_json, ensure_ascii=False), "id": gym_id},
                    )

        # Migrate candidates
        result = await conn.execute(
            text("""
            SELECT id, name_raw, parsed_json 
            FROM gym_candidates 
            WHERE parsed_json->'court'->'courts' IS NOT NULL 
              AND parsed_json->'court'->>'lighting' IS NOT NULL
        """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} candidates with court.lighting at parent level")

        for row in rows:
            cand_id, name, parsed_json = row
            if not parsed_json:
                continue

            new_json, modified = migrate_lighting_to_courts(parsed_json)

            if modified:
                candidate_count += 1
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Fixing candidate {cand_id} ({name})")

                before_dump = json.dumps(parsed_json.get("court", {}), ensure_ascii=False)[:200]
                logger.info(f"  Before: {before_dump}")

                after_dump = json.dumps(new_json.get("court", {}), ensure_ascii=False)[:200]
                logger.info(f"  After:  {after_dump}")

                if not dry_run:
                    await conn.execute(
                        text("UPDATE gym_candidates SET parsed_json = :json WHERE id = :id"),
                        {"json": json.dumps(new_json, ensure_ascii=False), "id": cand_id},
                    )

        if not dry_run:
            await conn.commit()

    await engine.dispose()

    logger.info("\nSummary:")
    logger.info(f"  Gyms to fix: {gym_count}")
    logger.info(f"  Candidates to fix: {candidate_count}")

    if dry_run:
        logger.info("\nRun with --apply to actually update the database.")


if __name__ == "__main__":
    asyncio.run(main())
