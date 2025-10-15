"""CLI utilities for geocoding missing coordinates."""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.gym import Gym
from app.models.gym_candidate import GymCandidate
from app.services.geocode import geocode

logger = logging.getLogger(__name__)

_ZERO_WIDTH_RE = re.compile(r"[\u200B\u200C\u200D\uFEFF]")
_POSTAL_PREFIX_RE = re.compile(r"^〒\s*\d{3}-\d{4}\s*")
_TEL_TRAIL_RE = re.compile(
    r"\s*(?:TEL|ＴＥＬ)(?:\s*[:：])?\s*[0-9０-９]{2,4}-[0-9０-９]{2,4}-[0-9０-９]{3,4}.*$",
    flags=re.IGNORECASE,
)

_TARGET_CHOICES = {"gyms", "candidates"}
_ORIGIN_CHOICES = {"all", "scraped"}


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
    parser.add_argument(
        "--origin",
        choices=sorted(_ORIGIN_CHOICES),
        default="all",
        help="Filter gyms by origin (all or scraped)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without applying updates",
    )
    return parser


def normalize_address(address: str | None) -> str:
    """Normalize address strings for geocoding."""

    if not address:
        return ""

    cleaned = _ZERO_WIDTH_RE.sub("", address)
    cleaned = cleaned.replace("　", " ")
    cleaned = _POSTAL_PREFIX_RE.sub("", cleaned)
    cleaned = _TEL_TRAIL_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


async def _load_records(
    session: AsyncSession,
    target: str,
    limit: int | None,
    origin: str,
) -> list[Gym | GymCandidate]:
    if target == "gyms":
        query = (
            select(Gym)
            .where(or_(Gym.latitude.is_(None), Gym.longitude.is_(None)))
            .where(Gym.address.isnot(None))
            .where(Gym.address != "")
            .order_by(Gym.id)
        )
        if origin == "scraped":
            query = query.where(
                or_(Gym.official_url.is_(None), Gym.official_url.notlike("manual:%"))
            )
    elif target == "candidates":
        query = (
            select(GymCandidate)
            .where(or_(GymCandidate.latitude.is_(None), GymCandidate.longitude.is_(None)))
            .where(GymCandidate.address_raw.isnot(None))
            .where(GymCandidate.address_raw != "")
            .order_by(GymCandidate.id)
        )
    else:  # pragma: no cover - validation should prevent this
        msg = f"Unsupported target: {target}"
        raise ValueError(msg)

    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def _process_records(
    session: AsyncSession,
    target: str,
    limit: int | None,
    origin: str,
    dry_run: bool,
) -> dict[str, int]:
    records = await _load_records(session, target, limit, origin)
    if not records:
        logger.info("No %s with missing coordinates", target)
        return {"tried": 0, "updated": 0, "skipped": 0}

    tried = 0
    updated = 0
    skipped = 0

    for record in records:
        tried += 1
        raw_address = record.address if target == "gyms" else record.address_raw
        normalized_address = normalize_address(raw_address)
        if not normalized_address:
            skipped += 1
            logger.info(
                "Skipping id=%s due to empty normalized address (raw=%r)",
                record.id,
                raw_address,
            )
            continue

        if raw_address and raw_address != normalized_address:
            logger.info(
                "Normalized address id=%s: %r -> %r",
                record.id,
                raw_address,
                normalized_address,
            )

        coords = await geocode(session, normalized_address)
        if coords is None:
            skipped += 1
            logger.info("Geocode miss id=%s with address=%r", record.id, normalized_address)
            continue

        latitude, longitude = coords
        latitude_missing = getattr(record, "latitude") is None
        longitude_missing = getattr(record, "longitude") is None
        lat_update = latitude_missing and latitude is not None
        lon_update = longitude_missing and longitude is not None

        if lat_update or lon_update:
            updated += 1
            if dry_run:
                logger.info(
                    "DRY-RUN: would update %s id=%s with lat=%s lon=%s",
                    target[:-1],
                    record.id,
                    latitude,
                    longitude,
                )
            else:
                if lat_update:
                    record.latitude = latitude
                if lon_update:
                    record.longitude = longitude
                if target == "gyms" and raw_address != normalized_address:
                    record.address = normalized_address
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
            logger.info(
                "Skipping id=%s due to unchanged coordinates (lat=%s lon=%s)",
                record.id,
                getattr(record, "latitude"),
                getattr(record, "longitude"),
            )

    return {"tried": tried, "updated": updated, "skipped": skipped}


async def geocode_missing_records(
    target: str,
    limit: int | None = None,
    origin: str = "all",
    dry_run: bool = False,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Geocode missing coordinates for gyms or candidates."""

    if target not in _TARGET_CHOICES:
        msg = f"Invalid target: {target}"
        raise ValueError(msg)
    if origin not in _ORIGIN_CHOICES:
        msg = f"Invalid origin: {origin}"
        raise ValueError(msg)

    if session is None:
        async with SessionLocal() as owned_session:
            summary = await _process_records(owned_session, target, limit, origin, dry_run)
            if not dry_run:
                await owned_session.commit()
            logger.info(
                "Finished geocoding %s: tried=%s, updated=%s, skipped=%s",
                target,
                summary["tried"],
                summary["updated"],
                summary["skipped"],
            )
            return summary

    summary = await _process_records(session, target, limit, origin, dry_run)
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
        summary = asyncio.run(
            geocode_missing_records(
                args.target,
                args.limit,
                origin=args.origin,
                dry_run=args.dry_run,
            )
        )
    except Exception:  # pragma: no cover - CLI safeguard
        logger.exception("Geocoding script failed")
        return 1

    logger.info("Summary: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
