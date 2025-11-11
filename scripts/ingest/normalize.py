"""Normalize parsed gym candidates into consistent payloads."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from app.services.geocode import geocode

from .normalize_municipal_chuo import normalize_municipal_chuo_payload
from .normalize_municipal_edogawa import normalize_municipal_edogawa_payload
from .normalize_municipal_koto import normalize_municipal_koto_payload
from .normalize_municipal_minato import normalize_municipal_minato_payload
from .normalize_municipal_sumida import normalize_municipal_sumida_payload
from .sites import site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)


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

_PREF_MAPS = {
    "dummy": _DUMMY_PREF_MAP,
    site_a.SITE_ID: _SITE_A_PREF_MAP,
}
_CITY_MAPS = {
    "dummy": _DUMMY_CITY_MAP,
    site_a.SITE_ID: _SITE_A_CITY_MAP,
}

_MUNICIPAL_NORMALIZERS = {
    "municipal_koto": normalize_municipal_koto_payload,
    "municipal_edogawa": normalize_municipal_edogawa_payload,
    "municipal_sumida": normalize_municipal_sumida_payload,
    "municipal_chuo": normalize_municipal_chuo_payload,
    "municipal_minato": normalize_municipal_minato_payload,
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


async def normalize_candidates(
    source: str, limit: int | None, geocode_missing: bool = False
) -> int:
    """Normalize address and parsed payloads for gym candidates."""

    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        candidate_query = (
            select(GymCandidate)
            .options(selectinload(GymCandidate.source_page))
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

        updated_ids: set[int] = set()
        processed_candidates: list[GymCandidate] = []

        municipal_normalizer = _MUNICIPAL_NORMALIZERS.get(source)
        pref_map = _PREF_MAPS.get(source)
        city_map = _CITY_MAPS.get(source)

        for candidate in candidates:
            changed = False
            parsed_json = candidate.parsed_json if isinstance(candidate.parsed_json, dict) else {}

            if municipal_normalizer is not None:
                page_url = candidate.source_page.url if candidate.source_page else ""
                result = municipal_normalizer(parsed_json, page_url=page_url)

                payload = dict(result.parsed_json)
                equipments = payload.get("equipments", [])
                filtered = _filter_equipments(equipment_slugs, equipments)
                if filtered != equipments:
                    payload["equipments"] = filtered

                if candidate.name_raw != result.name_raw:
                    candidate.name_raw = result.name_raw
                    changed = True
                if candidate.address_raw != result.address_raw:
                    candidate.address_raw = result.address_raw
                    changed = True
                if candidate.pref_slug != result.pref_slug:
                    candidate.pref_slug = result.pref_slug
                    changed = True
                if candidate.city_slug != result.city_slug:
                    candidate.city_slug = result.city_slug
                    changed = True
                if candidate.parsed_json != payload:
                    candidate.parsed_json = payload
                    changed = True

            else:
                if pref_map is None or city_map is None:
                    msg = f"Unsupported source: {source}"
                    raise ValueError(msg)

                pref_slug = _find_slug(candidate.address_raw, pref_map)
                city_slug = _find_slug(candidate.address_raw, city_map)

                if candidate.pref_slug != pref_slug:
                    candidate.pref_slug = pref_slug
                    changed = True
                if candidate.city_slug != city_slug:
                    candidate.city_slug = city_slug
                    changed = True

                current_json = parsed_json or {}
                equipments = (
                    current_json.get("equipments", []) if isinstance(current_json, dict) else []
                )
                filtered = _filter_equipments(equipment_slugs, equipments)
                if filtered != equipments:
                    new_payload = dict(current_json)
                    new_payload["equipments"] = filtered
                    candidate.parsed_json = new_payload
                    changed = True

            if changed:
                updated_ids.add(candidate.id)

            processed_candidates.append(candidate)

        await session.commit()

        if geocode_missing and processed_candidates:
            geocoded = 0
            for candidate in processed_candidates:
                if not candidate.address_raw:
                    continue
                if candidate.latitude is not None and candidate.longitude is not None:
                    continue

                coords = await geocode(session, candidate.address_raw)
                if coords is None:
                    continue

                latitude, longitude = coords
                geo_changed = False
                if candidate.latitude is None and latitude is not None:
                    candidate.latitude = latitude
                    geo_changed = True
                if candidate.longitude is None and longitude is not None:
                    candidate.longitude = longitude
                    geo_changed = True

                if geo_changed:
                    geocoded += 1
                    updated_ids.add(candidate.id)

            if geocoded:
                await session.flush()
                await session.commit()
            logger.info("Geocoded %s candidates", geocoded)

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
        len(updated_ids),
    )
    return 0


__all__ = ["normalize_candidates"]
