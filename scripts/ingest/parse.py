"""Parse scraped HTML into ``gym_candidates`` records."""

from __future__ import annotations

import logging
import re
from itertools import cycle
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage

from .parse_municipal_koto import parse_municipal_koto_page
from .sites import municipal_edogawa, municipal_koto, municipal_sumida, site_a
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


def _build_municipal_koto_payload(page: ScrapedPage) -> tuple[str, str | None, dict[str, Any]]:
    parsed = parse_municipal_koto_page(page.raw_html or "", page.url)
    name = parsed.name.strip()
    if not name:
        name = _extract_dummy_name(page.raw_html, page.url)
    address = parsed.address.strip() if isinstance(parsed.address, str) and parsed.address else None
    parsed_json: dict[str, Any] = {"site": municipal_koto.SITE_ID}
    parsed_json.update(parsed.to_payload())
    return name, address, parsed_json


def _build_municipal_sumida_payload(page: ScrapedPage) -> tuple[str, str | None, dict[str, Any]]:
    detail = municipal_sumida.parse(page.raw_html or "", url=page.url)
    name = detail.name.strip() or _extract_dummy_name(page.raw_html, page.url)
    address = detail.address.strip() if detail.address else None
    parsed_json: dict[str, Any] = {
        "site": municipal_sumida.SITE_ID,
        "detail_url": detail.detail_url or page.url,
        "official_url": detail.official_url,
        "notes": detail.notes,
    }
    return name, address, parsed_json


def _build_municipal_edogawa_payload(page: ScrapedPage) -> tuple[str, str | None, dict[str, Any]]:
    detail = municipal_edogawa.parse(page.raw_html or "", url=page.url)
    name = detail.name.strip() or _extract_dummy_name(page.raw_html, page.url)
    address = detail.address.strip() if detail.address else None
    parsed_json: dict[str, Any] = {
        "site": municipal_edogawa.SITE_ID,
        "detail_url": detail.detail_url or page.url,
        "postal_code": detail.postal_code,
        "tel": detail.tel,
    }
    return name, address, parsed_json


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
            elif source == municipal_sumida.SITE_ID:
                name_raw, address_raw, parsed_json = _build_municipal_sumida_payload(page)
            elif source == municipal_edogawa.SITE_ID:
                name_raw, address_raw, parsed_json = _build_municipal_edogawa_payload(page)
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
