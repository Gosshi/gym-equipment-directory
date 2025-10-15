"""CLI utilities for geocoding missing coordinates."""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import re
from collections.abc import Sequence
from datetime import datetime

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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logs per record",
    )
    parser.add_argument(
        "--why",
        action="store_true",
        help="Print reason breakdown",
    )
    parser.add_argument(
        "--dump-failures",
        type=str,
        default=None,
        help="CSV path to dump geocode failures",
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


def analyze_reasons(raw: str | None, clean: str) -> set[str]:
    reasons: set[str] = set()
    if not raw:
        reasons.add("empty_address")
    if raw and raw != clean:
        if re.search(r"[\u200B\u200C\u200D\uFEFF]", raw):
            reasons.add("zero_width_removed")
        if re.match(r"^〒\d{3}-\d{4}\s*", raw):
            reasons.add("postal_removed")
        if re.search(r"TEL[:：]?\s*\d{2,4}-\d{2,4}-\d{3,4}", raw, flags=re.IGNORECASE):
            reasons.add("tel_removed")
    if not clean:
        reasons.add("normalized_empty")
    return reasons


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
    verbose: bool,
    show_why: bool,
    dump_failures_path: str | None,
) -> dict[str, int | dict[str, int]]:
    records = await _load_records(session, target, limit, origin)
    if not records:
        logger.info("No %s with missing coordinates", target)
        return {"tried": 0, "updated": 0, "skipped": 0, "reasons": {}}

    tried = 0
    updated = 0
    skipped = 0
    reason_counts: dict[str, int] = {}
    fail_rows: list[tuple[str | int, str, str, str, str]] = []

    for record in records:
        tried += 1
        raw_address = record.address if target == "gyms" else record.address_raw
        normalized_address = normalize_address(raw_address)
        reasons = analyze_reasons(raw_address, normalized_address)

        if not normalized_address:
            skipped += 1
            for reason in reasons or {"normalized_empty"}:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if verbose:
                logger.info(
                    "SKIP id=%s normalized_empty raw=%r",
                    record.id,
                    raw_address,
                )
            fail_rows.append(
                (
                    record.id,
                    getattr(record, "name", ""),
                    raw_address or "",
                    normalized_address,
                    ",".join(sorted(reasons)) or "normalized_empty",
                )
            )
            continue

        if raw_address and raw_address != normalized_address and verbose:
            logger.info(
                "Normalized address id=%s: %r -> %r",
                record.id,
                raw_address,
                normalized_address,
            )

        try:
            coords = await geocode(session, normalized_address)
        except Exception:  # pragma: no cover - external provider failure path
            skipped += 1
            reason_counts["exception"] = reason_counts.get("exception", 0) + 1
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if verbose:
                logger.exception("EXC id=%s addr=%r", record.id, normalized_address)
            fail_rows.append(
                (
                    record.id,
                    getattr(record, "name", ""),
                    raw_address or "",
                    normalized_address,
                    ",".join(sorted(reasons | {"exception"})),
                )
            )
            continue

        if coords is None:
            skipped += 1
            reason_counts["provider_miss"] = reason_counts.get("provider_miss", 0) + 1
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if verbose:
                logger.info(
                    "MISS id=%s addr=%r reasons=%s",
                    record.id,
                    normalized_address,
                    ",".join(sorted(reasons)) or "provider_miss",
                )
            fail_rows.append(
                (
                    record.id,
                    getattr(record, "name", ""),
                    raw_address or "",
                    normalized_address,
                    ",".join(sorted(reasons | {"provider_miss"})),
                )
            )
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
            reason_counts["unchanged"] = reason_counts.get("unchanged", 0) + 1
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if verbose:
                logger.info(
                    "SKIP id=%s unchanged coords lat=%s lon=%s",
                    record.id,
                    getattr(record, "latitude"),
                    getattr(record, "longitude"),
                )
            fail_rows.append(
                (
                    record.id,
                    getattr(record, "name", ""),
                    raw_address or "",
                    normalized_address,
                    ",".join(sorted(reasons | {"unchanged"})),
                )
            )

    if dump_failures_path:
        write_header = not os.path.exists(dump_failures_path)
        with open(dump_failures_path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if write_header:
                writer.writerow(["id", "name", "raw_address", "clean_address", "reasons"])
            for row in fail_rows:
                writer.writerow(row)
        if verbose and fail_rows:
            logger.info(
                "Dumped %s failure rows to %s at %s",
                len(fail_rows),
                dump_failures_path,
                datetime.now().isoformat(timespec="seconds"),
            )

    if show_why:
        logger.info(
            "Reason breakdown: %s",
            {key: reason_counts.get(key, 0) for key in sorted(reason_counts)},
        )

    return {
        "tried": tried,
        "updated": updated,
        "skipped": skipped,
        "reasons": reason_counts,
    }


async def geocode_missing_records(
    target: str,
    limit: int | None = None,
    origin: str = "all",
    dry_run: bool = False,
    verbose: bool = False,
    show_why: bool = False,
    dump_failures_path: str | None = None,
    session: AsyncSession | None = None,
) -> dict[str, int | dict[str, int]]:
    """Geocode missing coordinates for gyms or candidates."""

    if target not in _TARGET_CHOICES:
        msg = f"Invalid target: {target}"
        raise ValueError(msg)
    if origin not in _ORIGIN_CHOICES:
        msg = f"Invalid origin: {origin}"
        raise ValueError(msg)

    if session is None:
        async with SessionLocal() as owned_session:
            summary = await _process_records(
                owned_session,
                target,
                limit,
                origin,
                dry_run,
                verbose,
                show_why,
                dump_failures_path,
            )
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

    summary = await _process_records(
        session,
        target,
        limit,
        origin,
        dry_run,
        verbose,
        show_why,
        dump_failures_path,
    )
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
                verbose=args.verbose,
                show_why=args.why,
                dump_failures_path=args.dump_failures,
            )
        )
    except Exception:  # pragma: no cover - CLI safeguard
        logger.exception("Geocoding script failed")
        return 1

    logger.info("Summary: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
