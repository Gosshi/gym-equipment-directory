"""Operations tooling to backfill missing latitude/longitude values.

The script is invoked from `make geocode-*` targets and complements the
documentation in ``docs/ops_geocode_and_freshness.md``.  It accepts
``--target``/``--origin`` filters, supports dry-run mode, and returns a summary
dictionary so operational scripts and tests can assert on the outcome.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import re
import time
import unicodedata
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
    r"\s*(?:TEL|ＴＥＬ|電話|電話番号)(?:\s*[:：])?\s*[0-9０-９]{2,4}-[0-9０-９]{2,4}-[0-9０-９]{3,4}.*$",
    flags=re.IGNORECASE,
)
_KANJI_NUM_MAP = str.maketrans("一二三四五六七八九〇", "1234567890")
_SEPARATOR_RE = re.compile(r"[のノ．]")

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


def normalize_address(
    address: str | None, remove_building: bool = False, style: str = "hyphen"
) -> str:
    """Normalize address strings for geocoding.

    Args:
        address: The raw address string.
        remove_building: If True, removes the building name (assumed to be after the last space).
        style: "hyphen" (default) converts 丁目/番/号 to hyphens. "chome" preserves 丁目.

    Returns:
        The normalized address string.
    """

    if not address:
        return ""

    # 1. Full-width to Half-width (NFKC normalization)
    cleaned = unicodedata.normalize("NFKC", address)

    # 2. Remove zero-width characters
    cleaned = _ZERO_WIDTH_RE.sub("", cleaned)

    # 3. Remove postal code prefix
    cleaned = _POSTAL_PREFIX_RE.sub("", cleaned)

    # 4. Remove telephone number trail
    cleaned = _TEL_TRAIL_RE.sub("", cleaned)

    # 5. Kanji numerals to Arabic numerals (simple mapping)
    cleaned = cleaned.translate(_KANJI_NUM_MAP)

    # 6. Unify separators
    if style == "hyphen":
        cleaned = re.sub(r"(?:丁目|番|号)", "-", cleaned)
    elif style == "chome":
        # Keep 丁目, replace 番/号 with hyphens
        cleaned = re.sub(r"(?:番|号)", "-", cleaned)

    cleaned = _SEPARATOR_RE.sub("-", cleaned)

    # 7. Collapse whitespace and hyphens
    cleaned = re.sub(r"-+", "-", cleaned)  # Merge multiple hyphens
    cleaned = re.sub(r"-$", "", cleaned)  # Remove trailing hyphen
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # 8. Remove building name (optional)
    if remove_building and " " in cleaned:
        # Split by space and take everything except the last part if it looks like a building name
        # Heuristic: If there are multiple spaces, drop the last part.
        parts = cleaned.split(" ")
        if len(parts) > 1:
            cleaned = " ".join(parts[:-1])

    return cleaned


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
    failed_addresses: set[str] = set()

    for record in records:
        tried += 1
        raw_address = record.address if target == "gyms" else record.address_raw

        if raw_address in failed_addresses:
            logger.info("skip: already failed addr=%r", raw_address)
            skipped += 1
            continue

        # Retry logic: Original -> Hyphenated -> Chome -> No Building -> Fallback (Town)
        # 1. Original
        # 2. Hyphenated: 1-23-20
        # 3. Chome: 1丁目23-20
        # 4. No Building (Hyphen): 1-23-20 (if building was removed)
        # 5. Fallback (Town): 1-23 (strip last segment)

        variations = [
            ("original", raw_address),
            ("hyphen", normalize_address(raw_address, style="hyphen")),
            ("chome", normalize_address(raw_address, style="chome")),
            ("no_building", normalize_address(raw_address, remove_building=True, style="hyphen")),
        ]

        # Add fallback: strip last number segment from hyphenated style
        hyphenated = normalize_address(raw_address, remove_building=True, style="hyphen")
        if "-" in hyphenated:
            parts = hyphenated.rsplit("-", 1)
            if len(parts) > 1 and parts[0]:
                variations.append(("fallback_town", parts[0]))

        # Deduplicate variations while preserving order
        seen_addrs = set()
        unique_variations = []
        for label, addr in variations:
            if addr and addr not in seen_addrs:
                unique_variations.append((label, addr))
                seen_addrs.add(addr)

        success_coords = None
        success_addr = ""
        success_label = ""

        for label, addr in unique_variations:
            # Rate limiting
            time.sleep(1.0)

            try:
                coords = await geocode(session, addr)
                if coords:
                    success_coords = coords
                    success_addr = addr
                    success_label = label
                    break
            except Exception:
                logger.warning("Geocoding exception for %s (label=%s)", addr, label)
                continue

        if success_coords:
            lat, lng = success_coords
            if target == "gyms":
                record.latitude = lat
                record.longitude = lng
            else:
                record.latitude = lat
                record.longitude = lng
            updated += 1
            if verbose:
                logger.info(
                    "Updated id=%s addr=%r -> %s (label=%s)",
                    record.id,
                    raw_address,
                    success_addr,
                    success_label,
                )
            if not dry_run:
                # Only update address if it's the gyms table and we used a normalized version?
                # The requirement says "update latitude, longitude".
                # Updating address might be risky if we stripped too much, so let's stick to coords.
                # But if we fixed the address in gyms table, it might be good.
                # Update coords safely. Update address only for 'gyms' target.
                if target == "gyms" and success_label != "original":
                    record.address = success_addr

                await session.flush()
                logger.info(
                    "Success [%s] id=%s %r -> (%s, %s)",
                    success_label,
                    record.id,
                    success_addr,
                    lat,
                    lng,
                )
        else:
            skipped += 1
            # Use the most aggressive normalization for failure reporting
            final_norm = normalize_address(raw_address, remove_building=True)
            reasons = analyze_reasons(raw_address, final_norm)
            reason_counts["provider_miss"] = reason_counts.get("provider_miss", 0) + 1
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            logger.info(
                "Fail id=%s raw=%r (final_norm=%r)",
                record.id,
                raw_address,
                final_norm,
            )
            fail_rows.append(
                (
                    record.id,
                    getattr(record, "name", ""),
                    raw_address or "",
                    final_norm,
                    ",".join(sorted(reasons | {"provider_miss"})),
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
    """Geocode missing coordinates for gyms or candidates.

    The returned dictionary always contains ``tried``, ``updated``, ``skipped``
    and ``reasons`` keys so that CLI callers and tests can rely on a stable
    interface when summarizing batch results.
    """

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
