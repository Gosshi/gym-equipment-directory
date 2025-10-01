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
    ScrapedPage,
    Source,
    SourceType,
)


async def _create_source(session: AsyncSession, title: str = "site_a") -> Source:
    source = Source(source_type=SourceType.official_site, title=title, url="https://example.com")
    session.add(source)
    await session.flush()
    return source


async def _create_scraped_page(session: AsyncSession, source_id: int, suffix: str) -> ScrapedPage:
    page = ScrapedPage(
        source_id=source_id,
        url=f"https://example.com/gym/{suffix}",
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
    status: CandidateStatus = CandidateStatus.new,
    pref: str = "tokyo",
    city: str = "koto",
    parsed_json: dict | None = None,
) -> GymCandidate:
    source = await _create_source(session, title=f"source-{name}")
    page = await _create_scraped_page(session, source.id, suffix=name)
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw=name,
        address_raw="東京都江東区豊洲1-2-3",
        pref_slug=pref,
        city_slug=city,
        latitude=35.6,
        longitude=139.7,
        parsed_json=parsed_json,
        status=status,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


async def _ensure_equipments(session: AsyncSession, slugs: list[str]) -> None:
    for slug in slugs:
        exists = await session.execute(select(Equipment).where(Equipment.slug == slug))
        if exists.scalar_one_or_none():
            continue
        equipment = Equipment(slug=slug, name=slug.replace("-", " "), category="machine")
        session.add(equipment)
    await session.commit()


@pytest.mark.asyncio
async def test_list_candidates_with_filters(app_client: AsyncClient, session: AsyncSession) -> None:
    ids = []
    for idx in range(3):
        candidate = await _create_candidate(
            session,
            name=f"ダミージム{idx}",
            status=CandidateStatus.new,
            parsed_json={"equipments": ["smith-machine"]},
        )
        ids.append(candidate.id)
    await _create_candidate(session, name="レビュー中", status=CandidateStatus.reviewing)

    resp = await app_client.get(
        "/admin/candidates",
        params={"status": "new", "limit": 2},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 2
    assert payload["next_cursor"]
    first_batch_ids = [item["id"] for item in payload["items"]]
    assert first_batch_ids == sorted(first_batch_ids, reverse=True)

    resp2 = await app_client.get(
        "/admin/candidates",
        params={"status": "new", "limit": 2, "cursor": payload["next_cursor"]},
    )
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert payload2["count"] == 1
    assert payload2["next_cursor"] is None


@pytest.mark.asyncio
async def test_candidate_detail_returns_page_info(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    candidate = await _create_candidate(session, name="詳細ジム")
    resp = await app_client.get(f"/admin/candidates/{candidate.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == candidate.id
    assert payload["scraped_page"]["url"].startswith("https://example.com/gym/詳細ジム")
    assert payload["scraped_page"]["http_status"] == 200


@pytest.mark.asyncio
async def test_patch_candidate_updates_pref_city(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    candidate = await _create_candidate(
        session,
        name="パッチ対象",
        pref="tokyo",
        city="koto",
    )
    resp = await app_client.patch(
        f"/admin/candidates/{candidate.id}",
        json={"pref_slug": "kanagawa", "city_slug": "yokohama"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["pref_slug"] == "kanagawa"
    assert payload["city_slug"] == "yokohama"


@pytest.mark.asyncio
async def test_approve_candidate_dry_run(app_client: AsyncClient, session: AsyncSession) -> None:
    await _ensure_equipments(
        session,
        ["smith-machine", "lat-pulldown"],
    )
    candidate = await _create_candidate(
        session,
        name="ドライランジム",
        parsed_json={"equipments": ["smith-machine", "lat-pulldown"]},
    )
    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve",
        json={"dry_run": True},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "preview" in payload
    assert payload["preview"]["equipments"]["total"] == 2
    assert "canonical_id" in payload["preview"]["gym"]
    refreshed = await session.get(GymCandidate, candidate.id)
    assert refreshed.status == CandidateStatus.new


@pytest.mark.asyncio
async def test_approve_candidate_commits(app_client: AsyncClient, session: AsyncSession) -> None:
    await _ensure_equipments(
        session,
        ["smith-machine", "dumbbell"],
    )
    candidate = await _create_candidate(
        session,
        name="承認ジム",
        parsed_json={"equipments": ["smith-machine", "dumbbell"]},
    )
    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/approve",
        json={
            "override": {
                "name": "承認ジム 最終",
                "pref_slug": "tokyo",
                "city_slug": "koto",
                "address": "東京都江東区豊洲1-2-3",
            }
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "result" in payload
    gym_slug = payload["result"]["gym"]["slug"]
    assert payload["result"]["gym"]["canonical_id"]
    gym_result = await session.execute(select(Gym).where(Gym.slug == gym_slug))
    gym_obj = gym_result.scalar_one_or_none()
    assert gym_obj is not None
    assert gym_obj.last_verified_at_cached is not None
    assert gym_obj.last_verified_at_cached.tzinfo is None
    refreshed_candidate = await session.get(GymCandidate, candidate.id)
    assert refreshed_candidate.status == CandidateStatus.approved


@pytest.mark.asyncio
async def test_approve_candidate_upserts_by_canonical_id(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    await _ensure_equipments(session, ["smith-machine"])

    candidate1 = await _create_candidate(
        session,
        name="カノニカルジム",
        parsed_json={"equipments": ["smith-machine"]},
    )

    resp1 = await app_client.post(
        f"/admin/candidates/{candidate1.id}/approve",
        json={"override": {"address": "東京都江東区豊洲1-2-3 1F"}},
    )
    assert resp1.status_code == 200
    result1 = resp1.json()["result"]["gym"]
    canonical_id = result1["canonical_id"]

    total_after_first = await session.scalar(select(func.count()).select_from(Gym))

    candidate2 = await _create_candidate(
        session,
        name="施設案内 ｜ カノニカルジム ｜江東区",
        parsed_json={"equipments": ["smith-machine"]},
    )

    resp2 = await app_client.post(
        f"/admin/candidates/{candidate2.id}/approve",
        json={
            "override": {
                "name": "カノニカルジム",
                "address": "東京都江東区豊洲5-6-7 別館",
            }
        },
    )
    assert resp2.status_code == 200
    result2 = resp2.json()["result"]["gym"]
    assert result2["canonical_id"] == canonical_id

    total_after_second = await session.scalar(select(func.count()).select_from(Gym))
    assert total_after_second == total_after_first


@pytest.mark.asyncio
async def test_reject_candidate_records_reason(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    candidate = await _create_candidate(session, name="却下ジム")
    resp = await app_client.post(
        f"/admin/candidates/{candidate.id}/reject",
        json={"reason": "重複"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "rejected"
    refreshed = await session.get(GymCandidate, candidate.id)
    assert refreshed.parsed_json.get("rejection_reason") == "重複"
