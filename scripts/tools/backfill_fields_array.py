"""Backfill fields array from existing scalar field columns.

Migrates data from field_type, field_count, field_lighting columns
to the new fields JSONB array format.

Usage:
    DATABASE_URL="..." python -m scripts.tools.backfill_fields_array [--dry-run]
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


async def migrate_field_data(session: AsyncSession, dry_run: bool = False) -> dict[str, int]:
    """Migrate scalar field columns to fields array."""

    stats = {
        "total": 0,
        "with_field_data": 0,
        "migrated": 0,
        "skipped": 0,
    }

    # Get all gyms with field data from parsed_json
    query = text("""
        SELECT id, parsed_json
        FROM gyms
        WHERE parsed_json IS NOT NULL
          AND (
              parsed_json->'meta'->>'field_type' IS NOT NULL
              OR parsed_json->'meta'->>'fields' IS NOT NULL
              OR (parsed_json->'field' IS NOT NULL AND parsed_json->'field' != 'null'::jsonb)
          )
    """)

    result = await session.execute(query)
    rows = result.fetchall()
    stats["total"] = len(rows)

    print(f"Found {len(rows)} gyms with potential field data")

    for row in rows:
        gym_id, parsed_json = row

        if not parsed_json:
            continue

        meta = parsed_json.get("meta", {})
        field_obj = parsed_json.get("field") or meta.get("field", {})

        # Extract scalar field values
        field_type = meta.get("field_type") or (
            field_obj.get("field_type") if isinstance(field_obj, dict) else None
        )
        field_count = meta.get("fields") or (
            field_obj.get("fields") if isinstance(field_obj, dict) else None
        )
        field_lighting = (
            meta.get("lighting")
            if "field" in parsed_json.get("meta", {}).get("categories", [])
            else None
        )
        if field_lighting is None and isinstance(field_obj, dict):
            field_lighting = field_obj.get("lighting")

        # Skip if no field data
        if not field_type and not field_count:
            continue

        stats["with_field_data"] += 1

        # Build fields array
        fields_array = []
        if field_type or field_count or field_lighting is not None:
            field_item: dict[str, Any] = {}
            if field_type:
                field_item["field_type"] = field_type
            if field_count:
                field_item["fields"] = field_count
            if field_lighting is not None:
                field_item["lighting"] = field_lighting

            if field_item:
                fields_array.append(field_item)

        if not fields_array:
            stats["skipped"] += 1
            continue

        print(f"  Gym ID {gym_id}: {len(fields_array)} field(s)")
        if dry_run:
            print(f"    [DRY RUN] Would set fields = {fields_array}")
        else:
            # Update gym with fields array - use raw execution
            await session.execute(
                text("UPDATE gyms SET fields = :fields WHERE id = :gym_id"),
                {"gym_id": gym_id, "fields": json.dumps(fields_array)},
            )
            stats["migrated"] += 1

    if not dry_run:
        await session.commit()

    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill fields array from scalar columns")
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
        print(f"Starting field data migration (dry_run={args.dry_run})...")
        stats = await migrate_field_data(session, dry_run=args.dry_run)

        print("\n=== Migration Summary ===")
        print(f"Total gyms checked: {stats['total']}")
        print(f"Gyms with field data: {stats['with_field_data']}")
        print(f"Gyms migrated: {stats['migrated']}")
        print(f"Gyms skipped: {stats['skipped']}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
