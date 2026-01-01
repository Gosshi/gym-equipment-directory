"""Migration script to fix old court format.

Moves `surface` from court level to individual court items, specifically for tennis courts.

Usage:
    # Dry run (preview changes)
    DATABASE_URL="postgresql+psycopg://..." python3 scripts/migrations/fix_court_surface_format.py

    # Apply changes
    DATABASE_URL="postgresql+psycopg://..." python3 \\
        scripts/migrations/fix_court_surface_format.py --apply
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

# Surfaces that are typically used for tennis courts
TENNIS_SURFACES = {
    "砂入り人工芝",
    "オムニコート",
    "オムニ",
    "クレー",
    "クレーコート",
    "ハードコート",
    "ハード",
    "人工芝",
    "天然芝",
    "アンツーカー",
}

# Court types that should receive the tennis surface
TENNIS_COURT_TYPES = {
    "テニス",
    "テニスコート",
    "庭球",
    "庭球場",
    "硬式テニス",
    "軟式テニス",
    "ソフトテニス",
}


def should_apply_surface_to_court(court_type: str | None, surface: str | None) -> bool:
    """Check if this surface should be applied to this court type."""
    if not court_type or not surface:
        return False

    is_tennis_surface = any(ts in surface for ts in TENNIS_SURFACES)
    if not is_tennis_surface:
        return False

    for tt in TENNIS_COURT_TYPES:
        if tt in court_type:
            return True

    return False


def fix_court_format(parsed_json: dict) -> tuple[dict, bool]:
    """Fix court format by moving surface to individual court items."""
    if not parsed_json:
        return parsed_json, False

    court = parsed_json.get("court")
    if not court or not isinstance(court, dict):
        return parsed_json, False

    courts = court.get("courts")
    parent_surface = court.get("surface")

    if not courts or not isinstance(courts, list) or not parent_surface:
        return parsed_json, False

    any_court_has_surface = any(isinstance(c, dict) and c.get("surface") for c in courts)

    if any_court_has_surface:
        return parsed_json, False

    modified = False
    new_courts = []

    for c in courts:
        if not isinstance(c, dict):
            new_courts.append(c)
            continue

        court_type = c.get("court_type")
        new_court = c.copy()

        if should_apply_surface_to_court(court_type, parent_surface):
            new_court["surface"] = parent_surface
            modified = True

        new_courts.append(new_court)

    if not modified:
        return parsed_json, False

    result = parsed_json.copy()
    result["court"] = court.copy()
    result["court"]["courts"] = new_courts

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
              AND parsed_json->'court'->>'surface' IS NOT NULL
        """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} gyms with court.surface")

        for row in rows:
            gym_id, slug, parsed_json = row
            if not parsed_json:
                continue

            new_json, modified = fix_court_format(parsed_json)

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
              AND parsed_json->'court'->>'surface' IS NOT NULL
        """)
        )
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} candidates with court.surface")

        for row in rows:
            cand_id, name, parsed_json = row
            if not parsed_json:
                continue

            new_json, modified = fix_court_format(parsed_json)

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
