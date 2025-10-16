from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
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
from app.models.gym_equipment import Availability

INTRO_BASE_URL = "https://example.com/sports_center3/introduction/"


async def _ensure_equipment(session: AsyncSession, slug: str) -> None:
    exists = await session.scalar(select(Equipment).where(Equipment.slug == slug))
    if exists:
        return
    equipment = Equipment(slug=slug, name=slug.replace("-", " "), category="machine")
    session.add(equipment)
    await session.commit()


async def _create_source(session: AsyncSession, title: str) -> Source:
    source = Source(source_type=SourceType.official_site, title=title, url="https://example.com")
    session.add(source)
    await session.flush()
    return source


async def _create_article_candidate(
    session: AsyncSession,
    *,
    page_path: str,
    name: str,
    pref: str,
    city: str,
    address: str | None = None,
    equipments: list[str] | None = None,
) -> GymCandidate:
    source = await _create_source(session, f"source-{name}")
    page = ScrapedPage(
        source_id=source.id,
        url=f"{INTRO_BASE_URL}{page_path}",
        fetched_at=datetime.now(UTC),
        http_status=200,
    )
    session.add(page)
    await session.flush()
    parsed_json = None
    if equipments:
        parsed_json = {"equipments": equipments}
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw=name,
        address_raw=address,
        pref_slug=pref,
        city_slug=city,
        status=CandidateStatus.new,
        parsed_json=parsed_json,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


async def _create_intro_gym(session: AsyncSession) -> Gym:
    gym = Gym(
        slug="koto-sports-center-3",
        name="江東区スポーツセンター",
        canonical_id="tokyo-koto-江東区スポーツセンター",
        pref="tokyo",
        city="koto",
        address="東京都江東区北砂1-2-3",
        official_url=INTRO_BASE_URL,
        last_verified_at_cached=datetime(2023, 1, 1, tzinfo=UTC).replace(tzinfo=None),
    )
    session.add(gym)
    await session.flush()
    await session.commit()
    return gym


@pytest.mark.asyncio
async def test_article_candidate_links_existing_gym(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    await _ensure_equipment(session, "leg-press")
    intro_gym = await _create_intro_gym(session)
    previous_last_verified = intro_gym.last_verified_at_cached
    candidate = await _create_article_candidate(
        session,
        page_path="trainingmachine.html",
        name="江東区スポーツセンター トレーニングルーム",
        pref="tokyo",
        city="koto",
        equipments=["leg-press"],
    )

    total_before = await session.scalar(select(func.count(Gym.id)))
    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve",
        json={"equipments": [{"slug": "leg-press", "availability": "present"}]},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["result"]["gym"]["slug"] == intro_gym.slug

    total_after = await session.scalar(select(func.count(Gym.id)))
    assert total_after == total_before

    refreshed = await session.get(Gym, intro_gym.id)
    assert refreshed is not None
    assert refreshed.last_verified_at_cached is not None
    assert refreshed.last_verified_at_cached > previous_last_verified

    leg_press_id = await session.scalar(select(Equipment.id).where(Equipment.slug == "leg-press"))
    link = await session.scalar(
        select(GymEquipment).where(
            GymEquipment.gym_id == intro_gym.id,
            GymEquipment.equipment_id == leg_press_id,
        )
    )
    assert link is not None
    assert link.availability == Availability.present

    candidate_refreshed = await session.get(GymCandidate, candidate.id)
    assert candidate_refreshed.status == CandidateStatus.approved


@pytest.mark.asyncio
async def test_article_candidate_without_address_is_rejected(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    candidate = await _create_article_candidate(
        session,
        page_path="tr_detail.html",
        name="トレーニングマシンの紹介",
        pref="tokyo",
        city="koto",
    )
    total_before = await session.scalar(select(func.count(Gym.id)))
    resp = await app_client.post(f"/admin/candidates/{candidate.id}/approve", json={})
    assert resp.status_code == 400
    total_after = await session.scalar(select(func.count(Gym.id)))
    assert total_after == total_before


@pytest.mark.asyncio
async def test_article_candidate_with_override_creates_new_gym(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    await _ensure_equipment(session, "chest-press")
    candidate = await _create_article_candidate(
        session,
        page_path="notes.html",
        name="利用上の注意",
        pref="tokyo",
        city="koto",
    )
    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve",
        json={
            "equipments": [{"slug": "chest-press", "availability": "present", "count": 2}],
            "override": {
                "name": "江東区スポーツセンター\u200b第2",
                "pref_slug": "tokyo",
                "city_slug": "koto",
                "address": "東京都江東区亀戸1-1-1\x00",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    result = payload["result"]["gym"]
    slug = result["slug"]
    assert "\u200b" not in slug
    assert "\x00" not in slug

    gym = await session.scalar(select(Gym).where(Gym.slug == slug))
    assert gym is not None
    assert "\u200b" not in gym.name
    assert "\x00" not in (gym.address or "")
    assert gym.official_url == f"{INTRO_BASE_URL}notes.html"
    chest_press_id = await session.scalar(
        select(Equipment.id).where(Equipment.slug == "chest-press")
    )
    link = await session.scalar(
        select(GymEquipment).where(
            GymEquipment.gym_id == gym.id,
            GymEquipment.equipment_id == chest_press_id,
        )
    )
    assert link is not None
    assert link.availability == Availability.present
    assert link.count == 2
