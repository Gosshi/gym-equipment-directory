"""Parse scraped HTML into ``gym_candidates`` records."""

from __future__ import annotations

import gc
import logging
import re
from itertools import cycle
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage

from .parse_municipal_edogawa import parse_municipal_edogawa_page
from .parse_municipal_generic import parse_municipal_page
from .parse_municipal_koto import parse_municipal_koto_page
from .parse_municipal_sumida import parse_municipal_sumida_page
from .sites import site_a
from .sources_registry import SOURCES
from .utils import get_or_create_source

logger = logging.getLogger(__name__)
BATCH_SIZE = 5

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


def _get_page_type(page: ScrapedPage) -> str | None:
    meta = page.response_meta or {}
    if isinstance(meta, dict):
        value = meta.get("municipal_page_type")
        if isinstance(value, str):
            return value
    return None


def _build_municipal_payload(
    page: ScrapedPage,
    *,
    source_id: str,
) -> tuple[str, str | None, dict[str, Any]] | None:
    source = SOURCES.get(source_id)
    if source_id == "municipal_koto":
        parser = parse_municipal_koto_page
    elif source_id == "municipal_edogawa":
        parser = parse_municipal_edogawa_page
    elif source_id == "municipal_sumida":
        parser = parse_municipal_sumida_page
    elif source is not None:
        parser = lambda html, url, page_type=None: parse_municipal_page(  # noqa: E731
            html,
            url,
            source=source,
            page_type=page_type,
        )
    else:
        msg = f"Unsupported municipal parser for source '{source_id}'"
        raise ValueError(msg)

    page_type = _get_page_type(page)
    parsed = parser(page.raw_html or "", page.url, page_type=page_type)

    if not parsed.meta.get("create_gym"):
        return None

    name = parsed.facility_name.strip()
    if not name:
        name = parsed.page_title.strip() or _extract_dummy_name(page.raw_html, page.url)
    address = parsed.address.strip() if isinstance(parsed.address, str) and parsed.address else None

    parsed_json: dict[str, Any] = {
        "facility_name": parsed.facility_name,
        "address": parsed.address,
        "equipments_raw": parsed.equipments_raw,
        "equipments": parsed.equipments,
        "center_no": parsed.center_no,
        "page_type": parsed.page_type,
        "page_title": parsed.page_title,
        "page_url": page.url,
        "meta": parsed.meta,
    }
    return name, address, parsed_json


async def parse_pages(source: str, limit: int | None) -> int:
    """Create or update ``gym_candidates`` from scraped pages."""

    # 1. Count total pages first
    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)
        count_query = select(func.count()).select_from(
            select(ScrapedPage.id).where(ScrapedPage.source_id == source_obj.id).subquery()
        )
        total_pages = (await session.execute(count_query)).scalar_one()
        source_id = source_obj.id  # Keep ID for subsequent queries

    if limit is not None:
        total_pages = min(total_pages, limit)
    if total_pages == 0:
        logger.info("No scraped pages available for source '%s'", source)
        return 0

    created = 0
    updated = 0
    sample_names: list[str] = []
    address_iter = cycle(_ADDRESS_POOL) if source == "dummy" else None
    equipment_iter = cycle(_EQUIPMENT_PATTERNS) if source == "dummy" else None
    processed = 0

    while processed < total_pages:
        batch_limit = min(BATCH_SIZE, total_pages - processed)

        # Open a fresh session for each batch to ensure memory is released
        async with SessionLocal() as session:
            base_query = (
                select(ScrapedPage)
                .where(ScrapedPage.source_id == source_id)
                .order_by(ScrapedPage.fetched_at.desc())
            )
            query = base_query.offset(processed).limit(batch_limit)
            pages = (await session.execute(query)).scalars().all()
            if not pages:
                break

            page_ids = [page.id for page in pages]
            existing_candidates = {}
            if page_ids:
                result = await session.execute(
                    select(GymCandidate).where(GymCandidate.source_page_id.in_(page_ids))
                )
                existing_candidates = {
                    candidate.source_page_id: candidate for candidate in result.scalars()
                }

            for page in pages:
                if source == "dummy":
                    assert address_iter is not None and equipment_iter is not None
                    name_raw, address_raw, parsed_json = _build_dummy_payload(
                        page, address_iter, equipment_iter
                    )
                elif source == site_a.SITE_ID:
                    name_raw, address_raw, parsed_json = _build_site_a_payload(page)
                elif source in SOURCES:
                    payload = _build_municipal_payload(page, source_id=source)
                    if payload is None:
                        continue
                    name_raw, address_raw, parsed_json = payload
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

        # Session is closed here
        processed += batch_limit
        gc.collect()

        logger.info("Processed %s/%s scraped pages for source '%s'", processed, total_pages, source)

    total = created + updated
    logger.info(
        "Processed %s scraped pages into candidates (created=%s, updated=%s)",
        total,
        created,
        updated,
    )
    if sample_names:
        suffix = "..." if total_pages > 2 else ""
        logger.info(
            "Sample candidate names: %s%s",
            ", ".join(sample_names),
            suffix,
        )
    return 0
