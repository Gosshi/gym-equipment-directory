"""Dummy fetch implementation that seeds ``scraped_pages`` records."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models.scraped_page import ScrapedPage

from .utils import get_or_create_source

logger = logging.getLogger(__name__)


def _generate_dummy_urls(limit: int) -> list[str]:
    return [f"https://example.local/gym/{i:03d}" for i in range(1, limit + 1)]


def _load_urls_from_file(file_path: Path, limit: int | None) -> list[str]:
    lines = [line.strip() for line in file_path.read_text().splitlines() if line.strip()]
    if limit is not None:
        return lines[:limit]
    return lines


async def fetch_pages(source: str, limit: int | None, file_path: Path | None) -> int:
    """Fetch (dummy) HTML pages and upsert into ``scraped_pages``."""
    limit = limit or 10
    if file_path is not None:
        urls = _load_urls_from_file(file_path, limit)
    else:
        urls = _generate_dummy_urls(limit)

    if not urls:
        logger.info("No URLs provided; nothing to fetch")
        return 0

    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        result = await session.execute(
            select(ScrapedPage).where(
                ScrapedPage.source_id == source_obj.id,
                ScrapedPage.url.in_(urls),
            )
        )
        existing_pages = {page.url: page for page in result.scalars()}

        now = datetime.now(timezone.utc)
        created = 0
        updated = 0
        for idx, url in enumerate(urls, start=1):
            raw_html = f"<html><title>Dummy Gym {idx:03d}</title></html>"
            if url in existing_pages:
                page = existing_pages[url]
                page.fetched_at = now
                page.raw_html = raw_html
                updated += 1
                continue

            page = ScrapedPage(
                source_id=source_obj.id,
                url=url,
                fetched_at=now,
                raw_html=raw_html,
                http_status=None,
            )
            session.add(page)
            created += 1

        await session.commit()

    total = created + updated
    preview = ", ".join(urls[:3])
    logger.info(
        "Upserted %s scraped pages (created=%s, updated=%s) for source '%s'", 
        total,
        created,
        updated,
        source,
    )
    logger.info("Sample URLs: %s%s", preview, "..." if len(urls) > 3 else "")
    return 0
