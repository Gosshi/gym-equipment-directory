from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateStatus,
    Gym,
    GymCandidate,
    GymEquipment,
    ScrapedPage,
    Source,
    SourceType,
)


async def _create_source(session: AsyncSession) -> Source:
    source = Source(
        source_type=SourceType.official_site, title="api-source", url="https://example.com"
    )
    session.add(source)
    await session.flush()
    return source


async def _create_page(session: AsyncSession, source_id: int, suffix: str) -> ScrapedPage:
    page = ScrapedPage(
        source_id=source_id,
        url=f"https://example.com/{suffix}",
        fetched_at=datetime.now(UTC),
        http_status=200,
    )
    session.add(page)
    await session.flush()
    return page


async def _create_candidate(session: AsyncSession, parsed_json: dict) -> GymCandidate:
    source = await _create_source(session)
    page = await _create_page(session, source.id, "auto")
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw=parsed_json.get("facility_name", "APIテストジム"),
        address_raw=parsed_json.get("address", "東京都江東区東砂4-24-1"),
        pref_slug="tokyo",
        city_slug="koto",
        latitude=35.6,
        longitude=139.8,
        parsed_json=parsed_json,
        status=CandidateStatus.new,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


@pytest.mark.asyncio
async def test_auto_approve_dry_run(app_client: AsyncClient, session: AsyncSession) -> None:
    parsed = {
        "meta": {"create_gym": True},
        "facility_name": "APIドライランジム",
        "address": "東京都江東区東砂4-24-1",
        "page_url": "https://example.com/sports_center2/introduction/tr_detail.html",
        "equipments_slotted": [{"slug": "seed-bench-press", "count": 3}],
    }
    candidate = await _create_candidate(session, parsed)

    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve-auto",
        params={"dry_run": "true"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dry_run"] is True
    assert payload["gym"]["action"] == "create"
    assert len(payload["equipments"]) == 1

    refreshed = await session.get(GymCandidate, candidate.id)
    assert refreshed.status is CandidateStatus.new


@pytest.mark.asyncio
async def test_auto_approve_commits(app_client: AsyncClient, session: AsyncSession) -> None:
    parsed = {
        "meta": {"create_gym": True},
        "facility_name": "API本承認ジム",
        "address": "東京都江東区東砂4-24-1",
        "page_url": "https://example.com/sports_center3/introduction/tr_detail.html",
        "equipments_slotted": [{"slug": "seed-lat-pulldown", "count": 2}],
    }
    candidate = await _create_candidate(session, parsed)

    resp = await app_client.post(f"/admin/candidates/{candidate.id}/approve-auto")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dry_run"] is False
    assert payload["candidate"]["status"] == CandidateStatus.approved.value

    refreshed_candidate = await session.get(GymCandidate, candidate.id)
    assert refreshed_candidate.status is CandidateStatus.approved

    gym_stmt = select(Gym).where(Gym.name == "API本承認ジム")
    gym = (await session.execute(gym_stmt)).scalars().first()
    assert gym is not None

    equipment_stmt = select(GymEquipment).where(GymEquipment.gym_id == gym.id)
    equipment_rows = (await session.execute(equipment_stmt)).scalars().all()
    assert len(equipment_rows) == 1
    assert equipment_rows[0].count == 2
