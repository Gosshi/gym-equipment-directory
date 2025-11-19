from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.ingest.approve import run_approval_batch
from tests.factories import create_candidate, create_page, create_source


def _session_factory(session: AsyncSession):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


@pytest.mark.asyncio
async def test_run_approval_batch_handles_multiple(session: AsyncSession) -> None:
    source = await create_source(session, "batch-source")
    page_one = await create_page(session, source.id, "batch-1")
    page_two = await create_page(session, source.id, "batch-2")

    parsed_one = {
        "meta": {"create_gym": True},
        "facility_name": "バッチジム1",
        "address": "東京都江東区辰巳1-1",
        "page_url": page_one.url,
    }
    parsed_two = {
        "meta": {"create_gym": True},
        "facility_name": "バッチジム2",
        "address": "東京都江東区辰巳2-2",
        "page_url": page_two.url,
    }
    candidate_one = await create_candidate(
        session,
        name="バッチジム1",
        page=page_one,
        parsed_json=parsed_one,
    )
    candidate_two = await create_candidate(
        session,
        name="バッチジム2",
        page=page_two,
        parsed_json=parsed_two,
    )

    results = await run_approval_batch(
        [candidate_one.id, candidate_two.id],
        dry_run=True,
        session_factory=_session_factory(session),
    )

    assert len(results) == 2
    assert all(item.success for item in results)
    assert all(item.payload for item in results)
    assert all(item.payload["dry_run"] is True for item in results)


@pytest.mark.asyncio
async def test_run_approval_batch_reports_missing_candidate(session: AsyncSession) -> None:
    results = await run_approval_batch(
        [999_999],
        dry_run=False,
        session_factory=_session_factory(session),
    )

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error == "candidate not found"
