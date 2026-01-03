"""Migrate field data in parsed_json from old format to new array format.

Old format: {"field": {"field_type": "野球場", "fields": 1, "lighting": true}}
New format: {"field": {"fields": [{"field_type": "野球場", "count": 1, "lighting": true}]}}

Usage:
    DATABASE_URL="..." python -m scripts.tools.migrate_field_to_array [--dry-run]
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


def convert_field_to_new_format(field_data: dict[str, Any]) -> dict[str, Any] | None:
    """Convert old field format to new array format.

    Old: {"field_type": "野球場", "fields": 1, "lighting": true}
    New: {"fields": [{"field_type": "野球場", "count": 1, "lighting": true}]}
    """
    if not isinstance(field_data, dict):
        return None

    # Check if already in new format (fields is an array)
    existing_fields = field_data.get("fields")
    if isinstance(existing_fields, list):
        return None  # Already migrated

    # Extract values from old format
    field_type = field_data.get("field_type")
    field_count = field_data.get("fields")  # In old format, this is an int
    lighting = field_data.get("lighting")

    if not field_type and not field_count:
        return None

    # Build new format item
    field_item: dict[str, Any] = {}
    if field_type:
        field_item["field_type"] = field_type
    if field_count is not None:
        field_item["count"] = field_count  # Rename from "fields" to "count"
    if lighting is not None:
        field_item["lighting"] = lighting

    if not field_item:
        return None

    return {"fields": [field_item]}


async def migrate_parsed_json_field(
    session: AsyncSession,
    table: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Migrate field data in parsed_json from old to new format."""

    stats = {
        "total": 0,
        "with_old_format": 0,
        "migrated": 0,
        "skipped": 0,
    }

    # Get all records with field data in parsed_json
    # We check for field object that has field_type directly (old format)
    # In new format, field would have "fields" as an array
    query = text(f"""
        SELECT id, parsed_json
        FROM {table}
        WHERE parsed_json IS NOT NULL
          AND parsed_json->'field' IS NOT NULL
          AND parsed_json->'field' != 'null'::jsonb
          AND jsonb_typeof(parsed_json->'field'->'fields') != 'array'
    """)

    result = await session.execute(query)
    rows = result.fetchall()
    stats["total"] = len(rows)

    print(f"Found {len(rows)} {table} with old field format")

    for row in rows:
        record_id, parsed_json = row

        if not parsed_json:
            continue

        field_data = parsed_json.get("field")
        if not field_data:
            stats["skipped"] += 1
            continue

        new_field = convert_field_to_new_format(field_data)
        if not new_field:
            stats["skipped"] += 1
            continue

        stats["with_old_format"] += 1

        # Update parsed_json with new field format
        updated_json = dict(parsed_json)
        updated_json["field"] = new_field

        print(f"  {table} ID {record_id}: {field_data} -> {new_field}")

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
        description="Migrate field in parsed_json from old to new array format"
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
        print(f"Starting field format migration (dry_run={args.dry_run})...")
        print()

        # Migrate gyms table
        print("=== Migrating gyms table ===")
        gym_stats = await migrate_parsed_json_field(session, "gyms", dry_run=args.dry_run)

        print()

        # Migrate gym_candidates table
        print("=== Migrating gym_candidates table ===")
        candidate_stats = await migrate_parsed_json_field(
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
