"""Unit tests for gym_search service logic without talking to the DB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from app.repositories.interfaces import GymEquipmentSummaryRow
from app.services.gym_search import search_gyms

pytestmark = pytest.mark.unit


@dataclass
class _FakeGym:
    id: int
    slug: str
    name: str
    pref: str = "tokyo"
    city: str = "shinjuku"
    last_verified_at_cached: datetime | None = None


class _FakeGymRepository:
    def __init__(self, gyms: list[_FakeGym], equipment_rows: list[GymEquipmentSummaryRow]) -> None:
        self._gyms = gyms
        self._equipment_rows = equipment_rows
        self.fetch_calls: list[tuple[list[int], list[str] | None]] = []

    async def list_by_pref_city(self, *, pref: str | None, city: str | None) -> list[_FakeGym]:
        self.list_args = {"pref": pref, "city": city}
        return self._gyms

    async def fetch_equipment_for_gyms(
        self,
        *,
        gym_ids: list[int],
        equipment_slugs: list[str] | None,
    ) -> list[GymEquipmentSummaryRow]:
        self.fetch_calls.append((list(gym_ids), list(equipment_slugs) if equipment_slugs else None))
        return list(self._equipment_rows)

    async def created_at_map(self, gym_ids: list[int]) -> dict[int, datetime | None]:
        self.created_at_inputs = list(gym_ids)
        return {gid: None for gid in gym_ids}


class _FakeUnitOfWork:
    def __init__(self, gym_repo: _FakeGymRepository) -> None:
        self.gyms = gym_repo


@pytest.mark.asyncio
async def test_search_filters_to_gyms_with_all_requested_equipments() -> None:
    gyms = [
        _FakeGym(id=1, slug="alpha-gym", name="Alpha Gym"),
        _FakeGym(id=2, slug="beta-gym", name="Beta Gym"),
    ]
    rows = [
        GymEquipmentSummaryRow(
            gym_id=1,
            slug="rack",
            name="Power Rack",
            category=None,
            count=3,
            max_weight_kg=90.0,
            availability="present",
            verification_status="verified",
            last_verified_at=datetime(2024, 5, 1, 12, 0, 0),
            source=None,
        ),
        GymEquipmentSummaryRow(
            gym_id=1,
            slug="bench",
            name="Bench Press",
            category=None,
            count=1,
            max_weight_kg=None,
            availability="present",
            verification_status="verified",
            last_verified_at=datetime(2024, 5, 5, 18, 30, 0),
            source=None,
        ),
        GymEquipmentSummaryRow(
            gym_id=2,
            slug="bench",
            name="Bench Press",
            category=None,
            count=4,
            max_weight_kg=100.0,
            availability="present",
            verification_status="verified",
            last_verified_at=datetime(2024, 4, 20, 9, 0, 0),
            source=None,
        ),
    ]
    repo = _FakeGymRepository(gyms, rows)
    uow = _FakeUnitOfWork(repo)

    page = await search_gyms(
        uow,
        pref="tokyo",
        city=None,
        equipments=["rack", "bench"],
        equipment_match="all",
        sort="richness",
        page_token=None,
        page=1,
        per_page=10,
    )

    assert [item.id for item in page.items] == [1]
    assert page.total == 1
    assert page.items[0].score == pytest.approx(2.5)
    assert page.items[0].last_verified_at == datetime(2024, 5, 5, 18, 30).isoformat()
    assert repo.fetch_calls == [([1, 2], ["rack", "bench"])], "equipment filter should be forwarded"


@pytest.mark.asyncio
async def test_search_sorts_by_latest_verification_when_sorting_by_freshness() -> None:
    gyms = [
        _FakeGym(
            id=1,
            slug="alpha-gym",
            name="Alpha Gym",
            last_verified_at_cached=datetime(2024, 1, 10, 9, 0, 0),
        ),
        _FakeGym(id=2, slug="beta-gym", name="Beta Gym"),
    ]
    rows = [
        GymEquipmentSummaryRow(
            gym_id=1,
            slug="rack",
            name="Power Rack",
            category=None,
            count=2,
            max_weight_kg=80.0,
            availability="present",
            verification_status="verified",
            last_verified_at=datetime(2024, 1, 5, 8, 0, 0),
            source=None,
        ),
        GymEquipmentSummaryRow(
            gym_id=2,
            slug="bench",
            name="Bench Press",
            category=None,
            count=2,
            max_weight_kg=90.0,
            availability="present",
            verification_status="verified",
            last_verified_at=datetime(2024, 2, 1, 10, 0, 0),
            source=None,
        ),
    ]
    repo = _FakeGymRepository(gyms, rows)
    uow = _FakeUnitOfWork(repo)

    page = await search_gyms(
        uow,
        pref=None,
        city=None,
        equipments=None,
        equipment_match="any",
        sort="freshness",
        page_token=None,
        page=1,
        per_page=10,
    )

    assert [item.id for item in page.items] == [2, 1]
    assert page.items[0].last_verified_at == datetime(2024, 2, 1, 10, 0).isoformat()
    assert page.items[1].last_verified_at == datetime(2024, 1, 10, 9, 0).isoformat()
    assert page.has_more is False
    assert page.has_prev is False
    assert page.page_token is None
