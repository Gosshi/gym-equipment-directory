"""Batch update gym slugs to hierarchical format.

Updates all gym slugs from flat format (e.g., 'kamiigusa-sports-center-suginami-tokyo')
to hierarchical format (e.g., 'tokyo/suginami/kamiigusa-sports-center').

Usage:
    # Dry run to preview changes
    python -m scripts.tools.update_slugs --dry-run

    # Run actual update
    python -m scripts.tools.update_slugs

    # Limit to first N records
    python -m scripts.tools.update_slugs --limit 10 --dry-run

    # Export old->new slug mapping to CSV
    python -m scripts.tools.update_slugs --export-mapping slugs.csv --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.gym import Gym
from app.services.slug_generator import build_hierarchical_slug

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch update gym slugs to hierarchical format")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of records to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without applying updates",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logs per record",
    )
    parser.add_argument(
        "--export-mapping",
        type=str,
        default=None,
        help="CSV path to export old->new slug mapping (useful for redirects)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update even if slug already contains '/' (re-generate all)",
    )
    return parser


async def _load_gyms(
    session: AsyncSession,
    limit: int | None,
    force: bool,
) -> list[Gym]:
    """Load gyms that need slug updates."""
    query = select(Gym).order_by(Gym.id)

    if not force:
        # Only select gyms with flat slugs (no '/' in slug)
        query = query.where(~Gym.slug.contains("/"))

    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def _process_gyms(
    session: AsyncSession,
    limit: int | None,
    dry_run: bool,
    verbose: bool,
    export_path: str | None,
    force: bool,
) -> dict[str, int]:
    """Process gym slugs and update to hierarchical format."""
    gyms = await _load_gyms(session, limit, force)

    if not gyms:
        logger.info("No gyms found that need slug updates")
        return {"total": 0, "updated": 0, "skipped": 0, "errors": 0}

    total = len(gyms)
    updated = 0
    skipped = 0
    errors = 0
    mappings: list[tuple[int, str, str, str]] = []  # (id, name, old_slug, new_slug)

    for gym in gyms:
        old_slug = gym.slug

        try:
            new_slug = build_hierarchical_slug(
                name=gym.name,
                pref=gym.pref,
                city=gym.city,
            )
        except ValueError as e:
            logger.warning("Failed to generate slug for gym id=%s name=%r: %s", gym.id, gym.name, e)
            errors += 1
            continue

        if old_slug == new_slug:
            if verbose:
                logger.info("No change for gym id=%s slug=%s", gym.id, old_slug)
            skipped += 1
            continue

        # Check for duplicate slugs
        existing = await session.execute(
            select(Gym).where(Gym.slug == new_slug).where(Gym.id != gym.id)
        )
        if existing.scalar_one_or_none():
            logger.warning(
                "Duplicate slug detected for gym id=%s: %s -> %s (already exists)",
                gym.id,
                old_slug,
                new_slug,
            )
            errors += 1
            continue

        mappings.append((gym.id, gym.name, old_slug, new_slug))

        if verbose:
            logger.info(
                "gym id=%s: %s -> %s",
                gym.id,
                old_slug,
                new_slug,
            )

        if not dry_run:
            gym.slug = new_slug
            await session.flush()

        updated += 1

    # Export mapping if requested
    if export_path and mappings:
        with open(export_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "name", "old_slug", "new_slug"])
            for row in mappings:
                writer.writerow(row)
        logger.info("Exported %d slug mappings to %s", len(mappings), export_path)

    return {
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


async def update_slugs(
    limit: int | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    export_path: str | None = None,
    force: bool = False,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Update gym slugs to hierarchical format.

    Args:
        limit: Maximum number of records to process
        dry_run: If True, don't commit changes
        verbose: If True, log each record
        export_path: Path to export old->new slug mapping CSV
        force: If True, update all slugs even if already hierarchical
        session: Optional database session (creates own if not provided)

    Returns:
        Dictionary with counts: total, updated, skipped, errors
    """
    if session is None:
        async with SessionLocal() as owned_session:
            summary = await _process_gyms(
                owned_session,
                limit,
                dry_run,
                verbose,
                export_path,
                force,
            )
            if not dry_run:
                await owned_session.commit()
            return summary

    return await _process_gyms(
        session,
        limit,
        dry_run,
        verbose,
        export_path,
        force,
    )


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args(argv)

    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info("Starting slug update (%s)", mode)

    try:
        summary = asyncio.run(
            update_slugs(
                limit=args.limit,
                dry_run=args.dry_run,
                verbose=args.verbose,
                export_path=args.export_mapping,
                force=args.force,
            )
        )
    except Exception:
        logger.exception("Slug update script failed")
        return 1

    logger.info(
        "Summary: total=%d, updated=%d, skipped=%d, errors=%d",
        summary["total"],
        summary["updated"],
        summary["skipped"],
        summary["errors"],
    )

    if args.dry_run:
        logger.info("This was a dry run. No changes were made.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
