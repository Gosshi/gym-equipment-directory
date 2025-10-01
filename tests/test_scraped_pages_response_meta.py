from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScrapedPage, Source, SourceType


@pytest.mark.asyncio
async def test_scraped_page_response_meta_persists(session: AsyncSession) -> None:
    source = Source(
        source_type=SourceType.official_site, title="meta-source", url="https://example.com"
    )
    session.add(source)
    await session.flush()

    page = ScrapedPage(
        source_id=source.id,
        url="https://example.com/gym/meta",
        fetched_at=datetime.now(UTC),
        http_status=200,
        response_meta={"etag": "abc123", "content_type": "text/html"},
    )
    session.add(page)
    await session.flush()
    await session.commit()

    stored = await session.get(ScrapedPage, page.id)
    assert stored is not None
    assert stored.response_meta == {"etag": "abc123", "content_type": "text/html"}
