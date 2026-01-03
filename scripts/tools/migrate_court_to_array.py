"""Migrate court data in parsed_json from old format to new array format.

Old format: {"court": {"court_type": "テニス", "courts": 4, "surface": "砂入り", ...}}
New format: {"court": {"courts": [{"court_type": "テニス", "count": 4, ...}]}}

Usage:
    DATABASE_URL="..." python -m scripts.tools.migrate_court_to_array [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def convert_court_to_new_format(court_data: dict[str, Any]) -> dict[str, Any] | None:
    """Convert old court format to new array format.

    Old: {"court_type": "テニス", "courts": 4, "surface": "砂入り", "lighting": true}
    New: {"courts": [{"court_type": "テニス", "count": 4, "surface": "砂入り", "lighting": true}]}
    """
    if not isinstance(court_data, dict):
        return None

    # Check if already in new format (courts is an array)
    existing_courts = court_data.get("courts")
    if isinstance(existing_courts, list):
        return None  # Already migrated

    # Extract values from old format
    court_type = court_data.get("court_type")
    court_count = court_data.get("courts")  # In old format, this is an int
    surface = court_data.get("surface")
    lighting = court_data.get("lighting")

    if court_type is None and court_count is None:
        return None

    # Build new format item
    court_item: dict[str, Any] = {}
    if court_type:
        court_item["court_type"] = court_type
    if court_count is not None:
        court_item["count"] = court_count  # Rename from "courts" to "count"
    if surface is not None:
        court_item["surface"] = surface
    if lighting is not None:
        court_item["lighting"] = lighting

    if not court_item:
        return None

    return {"courts": [court_item]}


async def migrate_parsed_json_court(
    session: AsyncSession,
    table: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Migrate court data in parsed_json from old to new format."""

    stats = {
        "total": 0,
        "with_old_format": 0,
        "migrated": 0,
        "skipped": 0,
    }

    # Get all records with court data in parsed_json
    # We check for court object that has courts as int (old format)
    # In new format, courts would be an array
    query = text(f"""
        SELECT id, parsed_json
        FROM {table}
        WHERE parsed_json IS NOT NULL
          AND parsed_json->'court' IS NOT NULL
          AND parsed_json->'court' != 'null'::jsonb
          AND jsonb_typeof(parsed_json->'court'->'courts') != 'array'
    """)

    result = await session.execute(query)
    rows = result.fetchall()
    stats["total"] = len(rows)

    print(f"Found {len(rows)} {table} with old court format")

    for row in rows:
        record_id, parsed_json = row

        if not parsed_json:
            continue

        court_data = parsed_json.get("court")
        if not court_data:
            stats["skipped"] += 1
            continue

        new_court = convert_court_to_new_format(court_data)
        if not new_court:
            stats["skipped"] += 1
            continue

        stats["with_old_format"] += 1

        # Update parsed_json with new court format
        updated_json = dict(parsed_json)
        updated_json["court"] = new_court

        print(f"  {table} ID {record_id}: {court_data} -> {new_court}")

        if not dry_run:
            await session.execute(
                text(f"UPDATE {table} SET parsed_json = :json WHERE id = :id"),
                {"id": record_id, "json": json.dumps(updated_json)},
            )
            stats["migrated"] += 1

    if not dry_run:
        await session.commit()

    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate court in parsed_json from old to new array format"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no database changes)")
    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        print(f"Starting court format migration (dry_run={args.dry_run})...")
        print()

        # Migrate gyms table
        print("=== Migrating gyms table ===")
        gym_stats = await migrate_parsed_json_court(session, "gyms", dry_run=args.dry_run)

        print()

        # Migrate gym_candidates table
        print("=== Migrating gym_candidates table ===")
        candidate_stats = await migrate_parsed_json_court(
            session, "gym_candidates", dry_run=args.dry_run
        )

        print("\n=== Migration Summary ===")
        print("Gyms:")
        print(f"  Total checked: {gym_stats['total']}")
        print(f"  With old format: {gym_stats['with_old_format']}")
        print(f"  Migrated: {gym_stats['migrated']}")
        print(f"  Skipped: {gym_stats['skipped']}")

        print("Candidates:")
        print(f"  Total checked: {candidate_stats['total']}")
        print(f"  With old format: {candidate_stats['with_old_format']}")
        print(f"  Migrated: {candidate_stats['migrated']}")
        print(f"  Skipped: {candidate_stats['skipped']}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
