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
from app.services.geocode import geocode

from .normalize_municipal_koto import merge_payloads, normalize_payload
from .sites import municipal_edogawa, municipal_koto, municipal_sumida, site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)


def _nkfc(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\x00", "").strip()


_KOTO_HINTS: tuple[str, ...] = (
    "有明",
    "亀戸",
    "深川",
    "東砂",
    "大島",
    "猿江",
    "豊洲",
    "辰巳",
    "南砂",
    "木場",
    "森下",
)


def _assign_pref_city_for_municipal_koto(
    addr: str | None,
    name: str | None,
    *,
    parsed: dict | None = None,
) -> tuple[str | None, str | None]:
    """Heuristic assignment for Koto ward facilities."""

    segments: list[str] = []
    if addr:
        segments.append(addr)
    if name:
        segments.append(name)
    if parsed and isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, str):
                segments.append(value)
            elif isinstance(value, list | tuple):
                segments.extend(str(item) for item in value if isinstance(item, str))

    if not segments:
        return None, None

    text = _nkfc(" ".join(segments))
    if "東京都" in text or "江東区" in text:
        return "tokyo", "koto"
    if any(hint in text for hint in _KOTO_HINTS):
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
_MUNICIPAL_SUMIDA_PREF_MAP = {
    "東京都": "tokyo",
}
_MUNICIPAL_SUMIDA_CITY_MAP = {
    "墨田区": "sumida",
}
_MUNICIPAL_EDOGAWA_PREF_MAP = {
    "東京都": "tokyo",
}
_MUNICIPAL_EDOGAWA_CITY_MAP = {
    "江戸川区": "edogawa",
}
_PREF_MAPS = {
    "dummy": _DUMMY_PREF_MAP,
    site_a.SITE_ID: _SITE_A_PREF_MAP,
    municipal_koto.SITE_ID: _MUNICIPAL_KOTO_PREF_MAP,
    municipal_sumida.SITE_ID: _MUNICIPAL_SUMIDA_PREF_MAP,
    municipal_edogawa.SITE_ID: _MUNICIPAL_EDOGAWA_PREF_MAP,
}
_CITY_MAPS = {
    "dummy": _DUMMY_CITY_MAP,
    site_a.SITE_ID: _SITE_A_CITY_MAP,
    municipal_koto.SITE_ID: _MUNICIPAL_KOTO_CITY_MAP,
    municipal_sumida.SITE_ID: _MUNICIPAL_SUMIDA_CITY_MAP,
    municipal_edogawa.SITE_ID: _MUNICIPAL_EDOGAWA_CITY_MAP,
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
        pref_map = _PREF_MAPS.get(source)
        city_map = _CITY_MAPS.get(source)
        if pref_map is None or city_map is None:
            msg = f"Unsupported source: {source}"
            raise ValueError(msg)

        processed_candidates: list[GymCandidate] = []
        center_primary: dict[str, GymCandidate] = {}
        for candidate in candidates:
            if (
                source != municipal_koto.SITE_ID
                and (not candidate.name_raw or not candidate.address_raw)
            ):
                logger.warning(
                    "Skipping candidate id=%s for source '%s' due to missing name/address",
                    candidate.id,
                    source,
                )
                continue

            processed_candidates.append(candidate)

            pref_slug = _find_slug(candidate.address_raw, pref_map)
            city_slug = _find_slug(candidate.address_raw, city_map)

            current_json = candidate.parsed_json if isinstance(candidate.parsed_json, dict) else {}
            changed = False
            if source == municipal_koto.SITE_ID:
                normalized_payload = normalize_payload(current_json)
                if normalized_payload != current_json:
                    candidate.parsed_json = normalized_payload
                    current_json = normalized_payload
                    changed = True
                center_no = current_json.get("center_no")
                if isinstance(center_no, str) and center_no:
                    primary = center_primary.get(center_no)
                    if primary is None:
                        center_primary[center_no] = candidate
                    else:
                        merged = merge_payloads(
                            primary.parsed_json if isinstance(primary.parsed_json, dict) else {},
                            current_json,
                        )
                        if merged != primary.parsed_json:
                            primary.parsed_json = merged
                            updated_ids.add(primary.id)
                        if not primary.name_raw and candidate.name_raw:
                            primary.name_raw = candidate.name_raw
                            updated_ids.add(primary.id)
                        if not primary.address_raw and candidate.address_raw:
                            primary.address_raw = candidate.address_raw
                            updated_ids.add(primary.id)
                        if candidate.duplicate_of_id != primary.id:
                            candidate.duplicate_of_id = primary.id
                            changed = True

            if source == municipal_koto.SITE_ID and (not pref_slug or not city_slug):
                fallback_pref, fallback_city = _assign_pref_city_for_municipal_koto(
                    candidate.address_raw,
                    candidate.name_raw,
                    parsed=candidate.parsed_json
                    if isinstance(candidate.parsed_json, dict)
                    else None,
                )
                pref_slug = pref_slug or fallback_pref
                city_slug = city_slug or fallback_city

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
                updated_ids.add(candidate.id)

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
                changed = False
                if candidate.latitude is None and latitude is not None:
                    candidate.latitude = latitude
                    changed = True
                if candidate.longitude is None and longitude is not None:
                    candidate.longitude = longitude
                    changed = True

                if changed:
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
