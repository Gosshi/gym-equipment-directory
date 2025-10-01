"""Parse scraped HTML into ``gym_candidates`` records."""

from __future__ import annotations

import logging
import re
import unicodedata
from itertools import cycle
from typing import Any, Iterable
from urllib.parse import urlparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage

from .sites import municipal_koto, site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_ADDRESS_POOL = (
    "東京都江東区豊洲1-1-1",
    "大阪府大阪市北区梅田1-1-1",
    "北海道札幌市中央区北1条西1丁目",
)
_EQUIPMENT_PATTERNS = (
    ["smith-machine", "bench-press"],
    ["squat-rack", "dumbbell"],
)

_MUNICIPAL_KOTO_EQUIPMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "smith-machine": ("スミスマシン", "スミス", "smith machine"),
    "bench-press": ("ベンチプレス", "ベンチプレス台"),
    "dumbbell": ("ダンベル", "ダンベルセット"),
    "lat-pulldown": ("ラットプルダウン", "ラットプル"),
    "leg-press": ("レッグプレス", "レッグプレスマシン"),
    "upright-bike": ("エアロバイク", "バイク", "フィットネスバイク"),
    "leg-extension": ("レッグエクステンション",),
    "chest-press": ("チェストプレス", "チェストプレスマシン"),
}


def _normalize_equipment_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip().lower()
    return normalized.replace(" ", "").replace("\u3000", "")


_MUNICIPAL_KOTO_LOOKUP: dict[str, str] = {}
for slug, variants in _MUNICIPAL_KOTO_EQUIPMENT_ALIASES.items():
    for variant in variants:
        _MUNICIPAL_KOTO_LOOKUP[_normalize_equipment_key(variant)] = slug


def map_municipal_koto_equipments(equipments: Iterable[str]) -> list[str]:
    slugs: list[str] = []
    seen: set[str] = set()
    for item in equipments:
        key = _normalize_equipment_key(item)
        slug = _MUNICIPAL_KOTO_LOOKUP.get(key)
        if slug is None or slug in seen:
            continue
        slugs.append(slug)
        seen.add(slug)
    return slugs


def _extract_dummy_name(raw_html: str | None, url: str) -> str:
    if raw_html:
        match = _TITLE_RE.search(raw_html)
        if match:
            title = match.group(1).strip()
            if title:
                return title
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").title() or "Unnamed Gym"


def _build_dummy_payload(
    page: ScrapedPage,
    address_iter,
    equipment_iter,
) -> tuple[str, str, dict[str, Any]]:
    name_raw = _extract_dummy_name(page.raw_html, page.url)
    address_raw = next(address_iter)
    equipments = next(equipment_iter)
    parsed_json: dict[str, Any] = {"equipments": equipments}
    return name_raw, address_raw, parsed_json


def _build_site_a_payload(page: ScrapedPage) -> tuple[str, str, dict[str, Any]]:
    parsed = site_a.parse_gym_html(page.raw_html or "")
    parsed_json: dict[str, Any] = {
        "site": site_a.SITE_ID,
        "equipments": parsed.equipments,
        "equipments_raw": parsed.equipments_raw,
    }
    return parsed.name_raw, parsed.address_raw, parsed_json


def _build_municipal_koto_payload(page: ScrapedPage) -> tuple[str, str, dict[str, Any]]:
    detail = municipal_koto.parse_detail(page.raw_html or "")
    equipments_raw = municipal_koto.normalize_equipments(detail.equipments_raw)
    equipments = map_municipal_koto_equipments(equipments_raw)
    parsed_json: dict[str, Any] = {
        "site": municipal_koto.SITE_ID,
        "equipments": equipments,
        "equipments_raw": equipments_raw,
    }
    return detail.name, detail.address, parsed_json


async def parse_pages(source: str, limit: int | None) -> int:
    """Create or update ``gym_candidates`` from scraped pages."""

    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        query = (
            select(ScrapedPage)
            .where(ScrapedPage.source_id == source_obj.id)
            .order_by(ScrapedPage.fetched_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)

        pages = (await session.execute(query)).scalars().all()
        if not pages:
            logger.info("No scraped pages available for source '%s'", source)
            return 0

        page_ids = [page.id for page in pages]
        existing_candidates = {}
        if page_ids:
            result = await session.execute(
                select(GymCandidate).where(GymCandidate.source_page_id.in_(page_ids))
            )
            existing_candidates = {
                candidate.source_page_id: candidate for candidate in result.scalars()
            }

        created = 0
        updated = 0
        sample_names: list[str] = []
        address_iter = cycle(_ADDRESS_POOL) if source == "dummy" else None
        equipment_iter = cycle(_EQUIPMENT_PATTERNS) if source == "dummy" else None

        for page in pages:
            if source == "dummy":
                assert address_iter is not None and equipment_iter is not None
                name_raw, address_raw, parsed_json = _build_dummy_payload(
                    page, address_iter, equipment_iter
                )
            elif source == site_a.SITE_ID:
                name_raw, address_raw, parsed_json = _build_site_a_payload(page)
            elif source == municipal_koto.SITE_ID:
                name_raw, address_raw, parsed_json = _build_municipal_koto_payload(page)
            else:
                msg = f"Unsupported source: {source}"
                raise ValueError(msg)

            if name_raw and len(sample_names) < 2:
                sample_names.append(name_raw)

            candidate = existing_candidates.get(page.id)
            if candidate is None:
                candidate = GymCandidate(
                    source_page_id=page.id,
                    name_raw=name_raw,
                    address_raw=address_raw,
                    parsed_json=parsed_json,
                    status=CandidateStatus.new,
                )
                session.add(candidate)
                created += 1
                continue

            has_change = False
            if candidate.name_raw != name_raw:
                candidate.name_raw = name_raw
                has_change = True
            if candidate.address_raw != address_raw:
                candidate.address_raw = address_raw
                has_change = True
            if candidate.parsed_json != parsed_json:
                candidate.parsed_json = parsed_json
                has_change = True
            if has_change:
                updated += 1

        await session.commit()

    total = created + updated
    logger.info(
        "Processed %s scraped pages into candidates (created=%s, updated=%s)",
        total,
        created,
        updated,
    )
    if sample_names:
        suffix = "..." if len(pages) > 2 else ""
        logger.info(
            "Sample candidate names: %s%s",
            ", ".join(sample_names),
            suffix,
        )
    return 0
