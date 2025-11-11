from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateStatus,
    Equipment,
    Gym,
    GymCandidate,
    GymEquipment,
    ScrapedPage,
    Source,
    SourceType,
)
from app.services.approve_service import ApproveService


async def _create_source(session: AsyncSession, title: str) -> Source:
    source = Source(source_type=SourceType.official_site, title=title, url="https://example.com")
    session.add(source)
    await session.flush()
    return source


async def _create_page(session: AsyncSession, source_id: int, slug: str) -> ScrapedPage:
    page = ScrapedPage(
        source_id=source_id,
        url=f"https://example.com/{slug}",
        fetched_at=datetime.now(UTC),
        http_status=200,
    )
    session.add(page)
    await session.flush()
    return page


async def _create_candidate(
    session: AsyncSession,
    *,
    name: str,
    page: ScrapedPage,
    parsed_json: dict,
    status: CandidateStatus = CandidateStatus.new,
) -> GymCandidate:
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw=name,
        address_raw=parsed_json.get("address", "東京都江東区東砂4-24-1"),
        pref_slug="tokyo",
        city_slug="koto",
        latitude=35.6,
        longitude=139.8,
        parsed_json=parsed_json,
        status=status,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


@pytest.mark.asyncio
async def test_ignore_when_create_gym_false(session: AsyncSession) -> None:
    source = await _create_source(session, "ignore-source")
    page = await _create_page(session, source.id, "ignore")
    candidate = await _create_candidate(
        session,
        name="無視候補",
        page=page,
        parsed_json={"meta": {"create_gym": False}},
    )

    service = ApproveService(session)
    result = await service.approve(candidate.id, dry_run=False)
    assert result.candidate_status is CandidateStatus.ignored

    refreshed = await session.get(GymCandidate, candidate.id)
    assert refreshed is not None
    assert refreshed.status is CandidateStatus.ignored


@pytest.mark.asyncio
async def test_merge_into_target_gym(session: AsyncSession) -> None:
    existing_gym = Gym(
        name="既存ジム",
        slug="existing-gym",
        canonical_id="canonical-existing",
        pref="tokyo",
        city="koto",
        address=None,
    )
    session.add(existing_gym)
    await session.flush()

    source = await _create_source(session, "merge-source")
    page = await _create_page(session, source.id, "sports_center4/introduction/tr_detail.html")
    parsed = {
        "meta": {"create_gym": True, "target_gym_slug": "existing-gym"},
        "facility_name": "トレーニングルーム",
        "address": "東京都江東区東砂4-24-1",
        "page_url": page.url,
        "center_no": "4",
        "equipments_slotted": [{"slug": "seed-bench-press", "count": 2}],
    }
    candidate = await _create_candidate(session, name="既存ジム", page=page, parsed_json=parsed)

    service = ApproveService(session)
    result = await service.approve(candidate.id, dry_run=False)
    assert result.candidate_status is CandidateStatus.approved
    assert result.approved_gym_slug == "existing-gym"

    refreshed_gym = await session.get(Gym, existing_gym.id)
    assert refreshed_gym is not None
    assert refreshed_gym.address == "東京都江東区東砂4-24-1"

    stmt = select(GymEquipment).where(GymEquipment.gym_id == existing_gym.id)
    equipment_rows = (await session.execute(stmt)).scalars().all()
    assert len(equipment_rows) == 1
    assert equipment_rows[0].count == 2
    assert equipment_rows[0].last_verified_at is not None


@pytest.mark.asyncio
async def test_equipment_count_merges(session: AsyncSession) -> None:
    gym = Gym(
        name="マージジム",
        slug="merge-gym",
        canonical_id="canonical-merge",
        pref="tokyo",
        city="koto",
        address="東京都江東区",
    )
    session.add(gym)
    await session.flush()

    equipment = Equipment(slug="merge-machine", name="マージマシン", category="machine")
    session.add(equipment)
    await session.flush()

    existing = GymEquipment(
        gym_id=gym.id,
        equipment_id=equipment.id,
        count=None,
    )
    session.add(existing)
    await session.flush()
    await session.commit()

    source = await _create_source(session, "merge-count")
    page1 = await _create_page(session, source.id, "first")
    parsed1 = {
        "meta": {"create_gym": True, "target_gym_slug": "merge-gym"},
        "facility_name": "マージジム",
        "address": "東京都江東区",
        "page_url": page1.url,
        "equipments_slotted": [{"slug": "merge-machine", "count": 3}],
    }
    candidate1 = await _create_candidate(
        session,
        name="マージジム1",
        page=page1,
        parsed_json=parsed1,
    )

    service = ApproveService(session)
    await service.approve(candidate1.id, dry_run=False)

    refreshed = await session.get(GymEquipment, existing.id)
    assert refreshed is not None
    assert refreshed.count == 3

    page2 = await _create_page(session, source.id, "second")
    parsed2 = {
        "meta": {"create_gym": True, "target_gym_slug": "merge-gym"},
        "facility_name": "マージジム",
        "address": "東京都江東区",
        "page_url": page2.url,
        "equipments_slotted": [{"slug": "merge-machine", "count": 5}],
    }
    candidate2 = await _create_candidate(
        session,
        name="マージジム2",
        page=page2,
        parsed_json=parsed2,
    )

    await service.approve(candidate2.id, dry_run=False)
    refreshed_after = await session.get(GymEquipment, existing.id)
    assert refreshed_after.count == 5


@pytest.mark.asyncio
async def test_duplicate_candidates_do_not_duplicate_equipment(session: AsyncSession) -> None:
    source = await _create_source(session, "dup-source")
    page1 = await _create_page(session, source.id, "create-new")
    parsed1 = {
        "meta": {"create_gym": True},
        "facility_name": "新規ジム",
        "address": "東京都江東区",
        "page_url": page1.url,
        "equipments_slotted": [{"slug": "seed-lat-pulldown", "count": 1}],
    }
    candidate1 = await _create_candidate(session, name="新規ジム", page=page1, parsed_json=parsed1)

    service = ApproveService(session)
    await service.approve(candidate1.id, dry_run=False)

    gym_stmt = select(Gym).where(Gym.name == "新規ジム")
    gym_obj = (await session.execute(gym_stmt)).scalars().first()
    assert gym_obj is not None

    page2 = await _create_page(session, source.id, "reuse")
    parsed2 = {
        "meta": {"create_gym": True, "target_gym_slug": gym_obj.slug},
        "facility_name": "新規ジム",
        "address": "東京都江東区",
        "page_url": page2.url,
        "equipments_slotted": [{"slug": "seed-lat-pulldown", "count": 1}],
    }
    candidate2 = await _create_candidate(session, name="新規ジム2", page=page2, parsed_json=parsed2)

    await service.approve(candidate2.id, dry_run=False)

    stmt = select(GymEquipment).where(GymEquipment.gym_id == gym_obj.id)
    equipments = (await session.execute(stmt)).scalars().all()
    assert len(equipments) == 1
    assert equipments[0].count == 1
