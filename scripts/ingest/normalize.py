"""Normalize parsed gym candidates into consistent payloads using batched processing."""

from __future__ import annotations

import gc
import logging
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

from sqlalchemy import func, select
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

BATCH_SIZE = 50

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
    """Normalize address and parsed payloads for gym candidates using batch processing."""

    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        count_query = (
            select(func.count())
            .select_from(GymCandidate)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .where(ScrapedPage.source_id == source_obj.id)
        )
        total_candidates = (await session.execute(count_query)).scalar() or 0

        if total_candidates == 0:
            logger.info("No gym candidates found for source '%s'", source)
            return 0

        if limit is not None:
            total_candidates = min(total_candidates, limit)

        equipment_slugs = set((await session.execute(select(Equipment.slug))).scalars().all())

        processed_count = 0
        updated_count = 0

        municipal_normalizer = _MUNICIPAL_NORMALIZERS.get(source)
        pref_map = _PREF_MAPS.get(source)
        city_map = _CITY_MAPS.get(source)

        logger.info(
            "Starting normalization for %s candidates (source: %s)", total_candidates, source
        )

        while processed_count < total_candidates:
            current_limit = min(BATCH_SIZE, total_candidates - processed_count)

            candidate_query = (
                select(GymCandidate)
                .options(selectinload(GymCandidate.source_page))
                .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
                .where(ScrapedPage.source_id == source_obj.id)
                .order_by(GymCandidate.id)
                .offset(processed_count)
                .limit(current_limit)
            )

            result = await session.execute(candidate_query)
            candidates = result.scalars().fetchmany(current_limit)
            if not candidates:
                break

            batch_end = processed_count + len(candidates)
            logger.info(
                "処理中: %s-%s件目 / 全%s件 (batch size=%s)",
                processed_count + 1,
                batch_end,
                total_candidates,
                len(candidates),
            )

            batch_updated = 0
            geocoded_batch = 0

            for candidate in candidates:
                changed = False
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
                    batch_updated += 1

                if geocode_missing:
                    if candidate.address_raw and (
                        candidate.latitude is None or candidate.longitude is None
                    ):
                        coords = await geocode(session, candidate.address_raw)
                        if coords:
                            lat, lng = coords
                            if candidate.latitude is None:
                                candidate.latitude = lat
                            if candidate.longitude is None:
                                candidate.longitude = lng
                            batch_updated += 1
                            geocoded_batch += 1

            await session.commit()
            session.expunge_all()
            del candidates
            gc.collect()

            updated_count += batch_updated
            processed_count = batch_end

            if geocoded_batch > 0:
                logger.info("Geocoded %s candidates in batch", geocoded_batch)

    logger.info(
        "Normalized %s candidates (updated=%s)",
        processed_count,
        updated_count,
    )
    return 0


__all__ = ["normalize_candidates"]
