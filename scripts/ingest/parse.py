"""Parse dummy HTML into ``gym_candidates`` records."""

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


def _extract_name(raw_html: str | None, url: str) -> str:
    if raw_html:
        match = _TITLE_RE.search(raw_html)
        if match:
            title = match.group(1).strip()
            if title:
                return title
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").title() or "Unnamed Gym"


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
                candidate.source_page_id: candidate
                for candidate in result.scalars()
            }

        created = 0
        updated = 0
        address_iter = cycle(_ADDRESS_POOL)
        equipment_iter = cycle(_EQUIPMENT_PATTERNS)
        for page in pages:
            name_raw = _extract_name(page.raw_html, page.url)
            address_raw = next(address_iter)
            equipments = next(equipment_iter)
            parsed_json: dict[str, Any] = {"equipments": equipments}

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
    sample_names = ", ".join(
        [
            _extract_name(page.raw_html, page.url)
            for page in pages[:3]
        ]
    )
    logger.info(
        "Processed %s scraped pages into candidates (created=%s, updated=%s)",
        total,
        created,
        updated,
    )
    if sample_names:
        logger.info("Sample candidate names: %s%s", sample_names, "..." if len(pages) > 3 else "")
    return 0
