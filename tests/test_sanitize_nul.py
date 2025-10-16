from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateStatus,
    Equipment,
    Gym,
    GymCandidate,
    ScrapedPage,
    Source,
    SourceType,
)


async def _create_source(session: AsyncSession) -> Source:
    source = Source(
        source_type=SourceType.official_site, title="nul-source", url="https://example.com"
    )
    session.add(source)
    await session.flush()
    return source


async def _create_scraped_page(session: AsyncSession, source_id: int) -> ScrapedPage:
    page = ScrapedPage(
        source_id=source_id,
        url="https://example.com/gym/nul",
        fetched_at=datetime.now(UTC),
        http_status=200,
    )
    session.add(page)
    await session.flush()
    return page


async def _create_candidate(session: AsyncSession) -> GymCandidate:
    source = await _create_source(session)
    page = await _create_scraped_page(session, source.id)
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw="候補\u200b\x00ジム",
        address_raw="東京都\x00千代田区1-1-1\u200b",
        pref_slug="tokyo",
        city_slug="chiyoda",
        latitude=35.0,
        longitude=139.0,
        status=CandidateStatus.new,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


async def _ensure_equipment(session: AsyncSession, slug: str) -> None:
    exists = await session.execute(select(Equipment).where(Equipment.slug == slug))
    if exists.scalar_one_or_none():
        return
    equipment = Equipment(slug=slug, name="Dumbbell", category="free_weight")
    session.add(equipment)
    await session.commit()


@pytest.mark.asyncio
async def test_approve_candidate_strips_nul_characters(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    await _ensure_equipment(session, "dumbbell")
    candidate = await _create_candidate(session)

    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve",
        json={
            "dry_run": False,
            "override": {
                "name": "承認\x00\u200bジム",
                "address": "最終\x00住所\u200b",
                "pref_slug": "tokyo",
                "city_slug": "chiyoda",
            },
            "equipments": [{"slug": "dumbbell", "availability": "present"}],
        },
    )
    assert resp.status_code == 200

    gym = await session.scalar(select(Gym).order_by(Gym.id.desc()))
    assert gym is not None
    assert "\x00" not in gym.name
    assert "\x00" not in (gym.address or "")
    assert "\x00" not in gym.slug
    assert "\u200b" not in gym.name
    assert "\u200b" not in (gym.address or "")
    assert "\u200b" not in gym.slug
