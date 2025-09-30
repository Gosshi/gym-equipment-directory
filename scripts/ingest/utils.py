"""Utility helpers shared across ingest commands."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source, SourceType

logger = logging.getLogger(__name__)


async def get_or_create_source(
    session: AsyncSession,
    *,
    title: str,
    source_type: SourceType = SourceType.user_submission,
) -> Source:
    """Retrieve an existing source or create a new one."""
    result = await session.execute(
        select(Source).where(
            Source.source_type == source_type,
            Source.title == title,
        )
    )
    source = result.scalar_one_or_none()
    if source is not None:
        return source

    source = Source(source_type=source_type, title=title)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    logger.info("Created new source '%s' (%s)", title, source_type.value)
    return source
