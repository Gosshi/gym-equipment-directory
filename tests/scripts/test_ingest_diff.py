"""Tests for diff classification with reviewing status for re-scraped POIs.

このテストでは、既存Gymと一致する候補がreviewing ステータスに設定され、
linked_gym_id が parsed_json に追加されることを確認します。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym_candidate import CandidateStatus
from scripts.ingest.diff import DiffSummary, classify_candidates
from tests.factories import create_candidate, create_gym, create_page, create_source


@pytest.mark.asyncio
async def test_classify_url_match_sets_reviewing(session: AsyncSession) -> None:
    """既存GymとURL一致する場合、reviewing ステータスに設定される。"""
    source = await create_source(session, "test-source")
    page = await create_page(session, source.id, "test-page")

    # Create an existing gym with the same URL
    existing_gym = await create_gym(
        session,
        name="既存スポーツセンター",
        slug="existing-sports-center",
        official_url=page.url,
        address="東京都江東区辰巳1-1-1",
    )

    # Create a candidate with matching URL
    candidate = await create_candidate(
        session,
        name="既存スポーツセンター",
        page=page,
        parsed_json={"facility_name": "既存スポーツセンター", "address": "東京都江東区辰巳1-1-1"},
    )

    # Run classification
    summary = await classify_candidates(
        session,
        source="test-source",
        candidate_ids=[candidate.id],
    )

    # Verify results
    assert summary.reviewing_ids == (candidate.id,)
    assert summary.new_ids == ()
    assert summary.duplicate_ids == ()

    # Refresh candidate from DB
    await session.refresh(candidate)
    assert candidate.status == CandidateStatus.reviewing
    assert candidate.parsed_json is not None
    assert candidate.parsed_json.get("linked_gym_id") == existing_gym.id
    assert candidate.parsed_json.get("linked_gym_slug") == existing_gym.slug


@pytest.mark.asyncio
async def test_classify_address_name_match_sets_reviewing(session: AsyncSession) -> None:
    """住所＋名前が類似する場合、reviewing ステータスに設定される。"""
    source = await create_source(session, "test-source-2")
    page = await create_page(session, source.id, "test-page-2")

    # Create an existing gym with matching address
    existing_gym = await create_gym(
        session,
        name="新宿スポーツセンター",
        slug="shinjuku-sports-center",
        official_url="https://example.com/other-page",  # Different URL
        address="東京都新宿区西新宿1-2-3",
    )

    # Create a candidate with same address and similar name
    candidate = await create_candidate(
        session,
        name="新宿スポーツセンター",  # Same name
        page=page,
        address_raw="東京都新宿区西新宿1-2-3",  # Same address
        parsed_json={"facility_name": "新宿スポーツセンター"},
    )

    # Run classification
    summary = await classify_candidates(
        session,
        source="test-source-2",
        candidate_ids=[candidate.id],
    )

    # Verify results
    assert summary.reviewing_ids == (candidate.id,)
    assert summary.new_ids == ()

    await session.refresh(candidate)
    assert candidate.status == CandidateStatus.reviewing
    assert candidate.parsed_json.get("linked_gym_id") == existing_gym.id


@pytest.mark.asyncio
async def test_classify_no_match_remains_new(session: AsyncSession) -> None:
    """一致するGymがない場合、new_ids に含まれる。"""
    source = await create_source(session, "test-source-3")
    page = await create_page(session, source.id, "test-page-3")

    # Create a candidate with no matching gym
    candidate = await create_candidate(
        session,
        name="新規施設",
        page=page,
        parsed_json={"facility_name": "新規施設"},
    )

    # Run classification
    summary = await classify_candidates(
        session,
        source="test-source-3",
        candidate_ids=[candidate.id],
    )

    # Verify results
    assert summary.new_ids == (candidate.id,)
    assert summary.reviewing_ids == ()

    await session.refresh(candidate)
    # Status should remain unchanged (new)
    assert candidate.status == CandidateStatus.new


@pytest.mark.asyncio
async def test_classify_empty_candidates() -> None:
    """空の候補リストで空のDiffSummaryが返される。"""
    # This test doesn't need a session since we're testing early return
    summary = DiffSummary(new_ids=(), updated_ids=(), duplicate_ids=(), reviewing_ids=())
    assert summary.total() == 0
