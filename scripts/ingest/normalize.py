"""Normalize gym candidate records for supported sources."""

from __future__ import annotations

import logging
import unicodedata
from collections.abc import Iterable

from sqlalchemy import select

from app.db import SessionLocal
from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage

from .sites import municipal_koto, site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)


def _nkfc(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\x00", "").strip()


def _assign_pref_city_for_municipal_koto(addr: str | None) -> tuple[str | None, str | None]:
    """Heuristic assignment for Koto ward facilities."""

    if not addr:
        return None, None
    normalized = _nkfc(addr)
    if "江東区" in normalized or "東京都" in normalized:
        return "tokyo", "koto"
    return None, None


_DUMMY_PREF_MAP = {
    "東京都": "tokyo",
    "大阪府": "osaka",
    "北海道": "hokkaido",
}
_DUMMY_CITY_MAP = {
    "江東区": "koto",
    "大阪市北区": "osaka-kita",
    "札幌市中央区": "sapporo-chuo",
}
_SITE_A_PREF_MAP = {
    "東京都": "tokyo",
    "千葉県": "chiba",
}
_SITE_A_CITY_MAP = {
    "江東区": "koto",
    "墨田区": "sumida",
    "江戸川区": "edogawa",
    "品川区": "shinagawa",
    "港区": "minato",
    "船橋市": "funabashi",
    "習志野市": "narashino",
    "浦安市": "urayasu",
    "千葉市": "chiba",
    "美浜区": "mihama",
}
_MUNICIPAL_KOTO_PREF_MAP = {
    "東京都": "tokyo",
}
_MUNICIPAL_KOTO_CITY_MAP = {
    "江東区": "koto",
}
_PREF_MAPS = {
    "dummy": _DUMMY_PREF_MAP,
    site_a.SITE_ID: _SITE_A_PREF_MAP,
    municipal_koto.SITE_ID: _MUNICIPAL_KOTO_PREF_MAP,
}
_CITY_MAPS = {
    "dummy": _DUMMY_CITY_MAP,
    site_a.SITE_ID: _SITE_A_CITY_MAP,
    municipal_koto.SITE_ID: _MUNICIPAL_KOTO_CITY_MAP,
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

        equipment_slugs = set((await session.execute(select(Equipment.slug))).scalars().all())

        updated = 0
        pref_map = _PREF_MAPS.get(source)
        city_map = _CITY_MAPS.get(source)
        if pref_map is None or city_map is None:
            msg = f"Unsupported source: {source}"
            raise ValueError(msg)

        processed_candidates: list[GymCandidate] = []
        for candidate in candidates:
            if not candidate.name_raw or not candidate.address_raw:
                logger.warning(
                    "Skipping candidate id=%s for source '%s' due to missing name/address",
                    candidate.id,
                    source,
                )
                continue

            processed_candidates.append(candidate)

            pref_slug = _find_slug(candidate.address_raw, pref_map)
            city_slug = _find_slug(candidate.address_raw, city_map)

            if source == municipal_koto.SITE_ID and (not pref_slug or not city_slug):
                fallback_pref, fallback_city = _assign_pref_city_for_municipal_koto(
                    candidate.address_raw
                )
                pref_slug = pref_slug or fallback_pref
                city_slug = city_slug or fallback_city

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
        for candidate in processed_candidates[:2]
    ]
    if sample_updates:
        logger.info(
            "Sample normalized candidates: %s%s",
            "; ".join(sample_updates),
            "..." if len(processed_candidates) > 2 else "",
        )
    logger.info(
        "Normalized %s candidates (updated=%s)",
        len(processed_candidates),
        updated,
    )
    return 0
