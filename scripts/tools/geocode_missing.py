"""CLI utilities for geocoding missing coordinates."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.gym import Gym
from app.models.gym_candidate import GymCandidate
from app.services.geocode import geocode

logger = logging.getLogger(__name__)

_TARGET_CHOICES = {"gyms", "candidates"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Geocode missing gym coordinates")
    parser.add_argument(
        "--target",
        choices=sorted(_TARGET_CHOICES),
        required=True,
        help="Target table to update (gyms or candidates)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of records to process",
    )
    return parser


async def _load_records(
    session: AsyncSession, target: str, limit: int | None
) -> list[Gym | GymCandidate]:
    if target == "gyms":
        query = (
            select(Gym)
            .where(or_(Gym.latitude.is_(None), Gym.longitude.is_(None)))
            .where(Gym.address.isnot(None))
            .order_by(Gym.id)
        )
    elif target == "candidates":
        query = (
            select(GymCandidate)
            .where(or_(GymCandidate.latitude.is_(None), GymCandidate.longitude.is_(None)))
            .where(GymCandidate.address_raw.isnot(None))
            .order_by(GymCandidate.id)
        )
    else:  # pragma: no cover - validation should prevent this
        msg = f"Unsupported target: {target}"
        raise ValueError(msg)

    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def _process_records(session: AsyncSession, target: str, limit: int | None) -> dict[str, int]:
    records = await _load_records(session, target, limit)
    if not records:
        logger.info("No %s with missing coordinates", target)
        return {"tried": 0, "updated": 0, "skipped": 0}

    tried = 0
    updated = 0
    skipped = 0

    for record in records:
        tried += 1
        address = record.address if target == "gyms" else record.address_raw
        if not address:
            skipped += 1
            logger.info("Skipping id=%s due to missing address", record.id)
            continue

        coords = await geocode(session, address)
        if coords is None:
            skipped += 1
            continue

        latitude, longitude = coords
        changed = False
        if getattr(record, "latitude") is None and latitude is not None:
            record.latitude = latitude
            changed = True
        if getattr(record, "longitude") is None and longitude is not None:
            record.longitude = longitude
            changed = True

        if changed:
            updated += 1
            await session.flush()
            logger.info(
                "Updated %s id=%s with lat=%s lon=%s",
                target[:-1],
                record.id,
                latitude,
                longitude,
            )
        else:
            skipped += 1

    return {"tried": tried, "updated": updated, "skipped": skipped}


async def geocode_missing_records(
    target: str, limit: int | None = None, session: AsyncSession | None = None
) -> dict[str, int]:
    """Geocode missing coordinates for gyms or candidates."""

    if target not in _TARGET_CHOICES:
        msg = f"Invalid target: {target}"
        raise ValueError(msg)

    if session is None:
        async with SessionLocal() as owned_session:
            summary = await _process_records(owned_session, target, limit)
            await owned_session.commit()
            logger.info(
                "Finished geocoding %s: tried=%s, updated=%s, skipped=%s",
                target,
                summary["tried"],
                summary["updated"],
                summary["skipped"],
            )
            return summary

    summary = await _process_records(session, target, limit)
    logger.info(
        "Finished geocoding %s: tried=%s, updated=%s, skipped=%s",
        target,
        summary["tried"],
        summary["updated"],
        summary["skipped"],
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        summary = asyncio.run(geocode_missing_records(args.target, args.limit))
    except Exception:  # pragma: no cover - CLI safeguard
        logger.exception("Geocoding script failed")
        return 1

    logger.info("Summary: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
