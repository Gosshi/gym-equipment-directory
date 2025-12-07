"""Fetch implementation for ingest sources."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models.scraped_page import ScrapedPage

from .sites import municipal_edogawa, municipal_koto, municipal_sumida, site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)


def _generate_dummy_urls(limit: int) -> list[str]:
    return [f"https://example.local/gym/{i:03d}" for i in range(1, limit + 1)]


def _load_urls_from_file(file_path: Path, limit: int | None) -> list[str]:
    lines = [line.strip() for line in file_path.read_text().splitlines() if line.strip()]
    if limit is not None:
        return lines[:limit]
    return lines


def _build_dummy_entries(urls: Iterable[str]) -> list[tuple[str, str]]:
    return [
        (url, f"<html><title>Dummy Gym {idx:03d}</title></html>")
        for idx, url in enumerate(urls, start=1)
    ]


async def _upsert_scraped_pages(source: str, entries: Sequence[tuple[str, str]]) -> tuple[int, int]:
    async with SessionLocal() as session:
        source_obj = await get_or_create_source(session, title=source)

        urls = [url for url, _ in entries]
        result = await session.execute(
            select(ScrapedPage).where(
                ScrapedPage.source_id == source_obj.id,
                ScrapedPage.url.in_(urls),
            )
        )
        existing_pages = {page.url: page for page in result.scalars()}

        fetched_at = datetime.now(UTC)
        created = 0
        updated = 0
        for url, raw_html in entries:
            if url in existing_pages:
                page = existing_pages[url]
                page.fetched_at = fetched_at
                if page.raw_html != raw_html:
                    logger.info(f"Updating raw_html for {url}")
                    page.raw_html = raw_html
                else:
                    logger.info(f"No change in raw_html for {url}")
                updated += 1
                continue

            page = ScrapedPage(
                source_id=source_obj.id,
                url=url,
                fetched_at=fetched_at,
                raw_html=raw_html,
                http_status=None,
            )
            session.add(page)
            created += 1

        await session.commit()

    return created, updated


def _log_fetch_summary(
    source: str, entries: Sequence[tuple[str, str]], created: int, updated: int
) -> None:
    total = created + updated
    sample_urls = ", ".join(url for url, _ in entries[:2])
    logger.info(
        "Upserted %s scraped pages (created=%s, updated=%s) for source '%s'",
        total,
        created,
        updated,
        source,
    )
    if sample_urls:
        logger.info("Sample URLs: %s%s", sample_urls, "..." if len(entries) > 2 else "")


async def _fetch_dummy(source: str, limit: int | None, file_path: Path | None) -> int:
    limit = limit or 10
    if file_path is not None:
        urls = _load_urls_from_file(file_path, limit)
    else:
        urls = _generate_dummy_urls(limit)

    if not urls:
        logger.info("No URLs provided; nothing to fetch for source '%s'", source)
        return 0

    entries = _build_dummy_entries(urls)
    created, updated = await _upsert_scraped_pages(source, entries)
    _log_fetch_summary(source, entries, created, updated)
    return 0


async def _fetch_site_a(source: str, limit: int | None, file_path: Path | None) -> int:
    if file_path is not None:
        msg = "File input is not supported for source 'site_a'"
        raise ValueError(msg)

    entries = site_a.iter_seed_pages(limit)
    if not entries:
        logger.info("No URLs provided; nothing to fetch for source '%s'", source)
        return 0

    created, updated = await _upsert_scraped_pages(source, entries)
    _log_fetch_summary(source, entries, created, updated)
    return 0


async def _fetch_municipal_koto(source: str, limit: int | None, file_path: Path | None) -> int:
    if file_path is not None:
        msg = "File input is not supported for source 'municipal_koto'"
        raise ValueError(msg)

    raw_entries = municipal_koto.iter_seed_pages(limit)
    if not raw_entries:
        logger.info("No URLs provided; nothing to fetch for source '%s'", source)
        return 0

    entries: list[tuple[str, str]] = []
    for entry in raw_entries:
        if isinstance(entry, tuple) and len(entry) == 2:
            url, raw_html = entry
        elif isinstance(entry, dict):
            url = entry.get("url")
            raw_html = entry.get("html") or entry.get("raw_html") or entry.get("content")
            if raw_html is None:
                msg = (
                    "municipal_koto seed entry must include HTML content under "
                    "'html'/'raw_html'/'content'"
                )
                raise ValueError(msg)
        else:
            msg = "municipal_koto seed entries must be tuples or dicts"
            raise TypeError(msg)
        if not url:
            msg = "municipal_koto seed entry is missing a URL"
            raise ValueError(msg)
        entries.append((str(url), str(raw_html)))

    created, updated = await _upsert_scraped_pages(source, entries)
    _log_fetch_summary(source, entries, created, updated)
    return 0


async def _fetch_municipal_sumida(source: str, limit: int | None, file_path: Path | None) -> int:
    if file_path is not None:
        msg = "File input is not supported for source 'municipal_sumida'"
        raise ValueError(msg)

    raw_entries = municipal_sumida.iter_seed_pages(limit)
    if not raw_entries:
        logger.info("No URLs provided; nothing to fetch for source '%s'", source)
        return 0

    entries = [(str(url), str(html)) for url, html in raw_entries]
    created, updated = await _upsert_scraped_pages(source, entries)
    _log_fetch_summary(source, entries, created, updated)
    return 0


async def _fetch_municipal_edogawa(source: str, limit: int | None, file_path: Path | None) -> int:
    if file_path is not None:
        msg = "File input is not supported for source 'municipal_edogawa'"
        raise ValueError(msg)

    raw_entries = municipal_edogawa.iter_seed_pages(limit)
    if not raw_entries:
        logger.info("No URLs provided; nothing to fetch for source '%s'", source)
        return 0

    entries = [(str(url), str(html)) for url, html in raw_entries]
    created, updated = await _upsert_scraped_pages(source, entries)
    _log_fetch_summary(source, entries, created, updated)
    return 0


async def fetch_pages(source: str, limit: int | None, file_path: Path | None) -> int:
    """Fetch HTML pages for the requested ingest ``source``."""

    if source == "dummy":
        return await _fetch_dummy(source, limit, file_path)
    if source == site_a.SITE_ID:
        return await _fetch_site_a(source, limit, file_path)
    if source == municipal_koto.SITE_ID:
        return await _fetch_municipal_koto(source, limit, file_path)
    if source == municipal_sumida.SITE_ID:
        return await _fetch_municipal_sumida(source, limit, file_path)
    if source == municipal_edogawa.SITE_ID:
        return await _fetch_municipal_edogawa(source, limit, file_path)
    msg = f"Unsupported source: {source}"
    raise ValueError(msg)
