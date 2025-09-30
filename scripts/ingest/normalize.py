"""Normalize dummy gym candidate records."""

from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import select

from app.db import SessionLocal
from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage

from .utils import get_or_create_source

logger = logging.getLogger(__name__)

_PREF_MAP = {
    "東京都": "tokyo",
    "大阪府": "osaka",
    "北海道": "hokkaido",
}
_CITY_MAP = {
    "江東区": "koto",
    "大阪市北区": "osaka-kita",
    "札幌市中央区": "sapporo-chuo",
}


def _find_slug(address: str | None, mapping: dict[str, str]) -> str | None:
    if not address:
        return None
    for keyword, slug in mapping.items():
        if keyword in address:
            return slug
    return None


def _filter_equipments(valid_slugs: Iterable[str], equipments: Iterable[str]) -> list[str]:
    valid = set(valid_slugs)
    return [slug for slug in equipments if slug in valid]


async def normalize_candidates(source: str, limit: int | None) -> int:
    """Normalize address and parsed payloads for gym candidates."""
    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        candidate_query = (
            select(GymCandidate)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .where(ScrapedPage.source_id == source_obj.id)
            .order_by(GymCandidate.id)
        )
        if limit is not None:
            candidate_query = candidate_query.limit(limit)

        candidates = (await session.execute(candidate_query)).scalars().all()
        if not candidates:
            logger.info("No gym candidates found for source '%s'", source)
            return 0

        equipment_slugs = set(
            (await session.execute(select(Equipment.slug))).scalars().all()
        )

        updated = 0
        for candidate in candidates:
            pref_slug = _find_slug(candidate.address_raw, _PREF_MAP)
            city_slug = _find_slug(candidate.address_raw, _CITY_MAP)

            changed = False
            if candidate.pref_slug != pref_slug:
                candidate.pref_slug = pref_slug
                changed = True
            if candidate.city_slug != city_slug:
                candidate.city_slug = city_slug
                changed = True

            current_json = candidate.parsed_json or {}
            if isinstance(current_json, dict):
                equipments = current_json.get("equipments", [])
            else:
                equipments = []
            filtered = _filter_equipments(equipment_slugs, equipments)
            if filtered != equipments:
                new_payload = dict(current_json)
                new_payload["equipments"] = filtered
                candidate.parsed_json = new_payload
                changed = True

            if changed:
                updated += 1

        await session.commit()

    sample_updates = [
        f"id={candidate.id}: pref={candidate.pref_slug}, city={candidate.city_slug}"
        for candidate in candidates[:3]
    ]
    if sample_updates:
        logger.info(
            "Sample normalized candidates: %s%s",
            "; ".join(sample_updates),
            "..." if len(candidates) > 3 else "",
        )
    logger.info("Normalized %s candidate records", updated)
    return 0
