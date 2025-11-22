"""Normalize parsed gym candidates into consistent payloads."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from app.services.geocode import geocode

from .normalize_municipal_edogawa import normalize_municipal_edogawa_payload
from .normalize_municipal_generic import (
    MunicipalNormalizationResult,
    normalize_municipal_payload,
)
from .normalize_municipal_koto import normalize_municipal_koto_payload
from .normalize_municipal_sumida import normalize_municipal_sumida_payload
from .sites import site_a
from .sources_registry import SOURCES
from .utils import get_or_create_source

logger = logging.getLogger(__name__)

BATCH_SIZE = 200


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


def _build_municipal_normalizers() -> dict[
    str, Callable[[dict[str, Any], str], MunicipalNormalizationResult]
]:
    registry: dict[str, Callable[[dict[str, Any], str], MunicipalNormalizationResult]] = {
        "municipal_koto": normalize_municipal_koto_payload,
        "municipal_edogawa": normalize_municipal_edogawa_payload,
        "municipal_sumida": normalize_municipal_sumida_payload,
    }

    for source_id, source in SOURCES.items():
        if source_id in registry:
            continue
        registry[source_id] = partial(normalize_municipal_payload, source=source)

    return registry


_MUNICIPAL_NORMALIZERS = _build_municipal_normalizers()


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

        equipment_slugs = set((await session.execute(select(Equipment.slug))).scalars().all())

        base_query = (
            select(GymCandidate)
            .options(
                selectinload(GymCandidate.source_page).load_only(ScrapedPage.id, ScrapedPage.url)
            )
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .where(ScrapedPage.source_id == source_obj.id)
            .order_by(GymCandidate.id)
        )
        processed = 0
        updated_count = 0
        sample_updates: list[str] = []
        geocoded_total = 0
        last_id: int | None = None
        remaining = limit

        municipal_normalizer = _MUNICIPAL_NORMALIZERS.get(source)
        pref_map = _PREF_MAPS.get(source)
        city_map = _CITY_MAPS.get(source)
        while True:
            batch_limit = BATCH_SIZE if remaining is None else min(BATCH_SIZE, remaining)

            query = base_query
            if last_id is not None:
                query = query.where(GymCandidate.id > last_id)

            candidates = (await session.execute(query.limit(batch_limit))).scalars().all()
            if not candidates:
                if processed == 0:
                    logger.info("No gym candidates found for source '%s'", source)
                break

            last_id = candidates[-1].id
            processed += len(candidates)
            if remaining is not None:
                remaining -= len(candidates)
            geocode_targets: list[tuple[GymCandidate, bool]] = []

            for candidate in candidates:
                candidate_changed = False
                parsed_json = (
                    candidate.parsed_json if isinstance(candidate.parsed_json, dict) else {}
                )

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
                        candidate_changed = True
                    if candidate.address_raw != result.address_raw:
                        candidate.address_raw = result.address_raw
                        candidate_changed = True
                    if candidate.pref_slug != result.pref_slug:
                        candidate.pref_slug = result.pref_slug
                        candidate_changed = True
                    if candidate.city_slug != result.city_slug:
                        candidate.city_slug = result.city_slug
                        candidate_changed = True
                    if candidate.parsed_json != payload:
                        candidate.parsed_json = payload
                        candidate_changed = True

                else:
                    if pref_map is None or city_map is None:
                        msg = f"Unsupported source: {source}"
                        raise ValueError(msg)

                    pref_slug = _find_slug(candidate.address_raw, pref_map)
                    city_slug = _find_slug(candidate.address_raw, city_map)

                    if candidate.pref_slug != pref_slug:
                        candidate.pref_slug = pref_slug
                        candidate_changed = True
                    if candidate.city_slug != city_slug:
                        candidate.city_slug = city_slug
                        candidate_changed = True

                    current_json = parsed_json or {}
                    equipments = (
                        current_json.get("equipments", []) if isinstance(current_json, dict) else []
                    )
                    filtered = _filter_equipments(equipment_slugs, equipments)
                    if filtered != equipments:
                        new_payload = dict(current_json)
                        new_payload["equipments"] = filtered
                        candidate.parsed_json = new_payload
                        candidate_changed = True

                if geocode_missing and candidate.address_raw:
                    needs_geocode = candidate.latitude is None and candidate.longitude is None
                    if needs_geocode:
                        geocode_targets.append((candidate, candidate_changed))

                if candidate_changed:
                    updated_count += 1
                    if len(sample_updates) < 2:
                        sample_updates.append(
                            f"id={candidate.id}: pref={candidate.pref_slug}, "
                            f"city={candidate.city_slug}"
                        )

            if geocode_targets:
                geocoded = 0
                for candidate, already_changed in geocode_targets:
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
                        geocoded_total += 1
                        if not already_changed:
                            updated_count += 1
                        if len(sample_updates) < 2:
                            sample_updates.append(
                                f"id={candidate.id}: pref={candidate.pref_slug}, "
                                f"city={candidate.city_slug}"
                            )

                if geocoded:
                    await session.flush()
                    logger.info("Geocoded %s candidates in batch", geocoded)

            await session.commit()
            session.expunge_all()

            logger.info("Processed %s candidates for source '%s' so far", processed, source)

            if remaining is not None and remaining <= 0:
                break

    if sample_updates:
        logger.info(
            "Sample normalized candidates: %s%s",
            "; ".join(sample_updates),
            "..." if processed > len(sample_updates) else "",
        )
    logger.info(
        "Normalized %s candidates (updated=%s, geocoded=%s)",
        processed,
        updated_count,
        geocoded_total,
    )
    return 0


__all__ = ["normalize_candidates"]
