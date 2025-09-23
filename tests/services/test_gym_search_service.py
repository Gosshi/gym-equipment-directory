from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.repositories.interfaces import GymEquipmentSummaryRow
from app.services.gym_search import GymSearchService


class StubUnitOfWork:
    def __init__(self, gym_repo):
        self.gyms = gym_repo
        self.equipments = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        return False

    async def commit(self) -> None:  # pragma: no cover - not used
        return None

    async def rollback(self) -> None:  # pragma: no cover - not used
        return None


class FakeGymRepository:
    def __init__(self, gyms, equipment_rows):
        self._gyms = gyms
        self._equipment_rows = equipment_rows
        self.received_slugs = None

    async def list_by_pref_city(self, *, pref, city):  # noqa: D401
        return self._gyms

    async def fetch_equipment_for_gyms(self, *, gym_ids, equipment_slugs):
        self.received_slugs = equipment_slugs
        return [row for row in self._equipment_rows if row.gym_id in gym_ids]

    async def created_at_map(self, gym_ids):
        return {gid: datetime(2024, 1, 1) for gid in gym_ids}


@pytest.mark.asyncio
async def test_search_service_returns_summaries_with_scores():
    gym = SimpleNamespace(
        id=1,
        slug="gym-alpha",
        name="Gym Alpha",
        pref="tokyo",
        city="shibuya",
        last_verified_at_cached=datetime(2024, 1, 10),
    )

    equipment_row = GymEquipmentSummaryRow(
        gym_id=1,
        slug="rack",
        name="Power Rack",
        category="strength",
        count=2,
        max_weight_kg=100,
        availability="present",
        verification_status="verified",
        last_verified_at=datetime(2024, 1, 5),
        source=None,
    )

    repo = FakeGymRepository([gym], [equipment_row])
    service = GymSearchService(lambda: StubUnitOfWork(repo))

    result = await service.search(
        pref=None,
        city=None,
        equipments=None,
        equipment_match="any",
        sort="freshness",
        page_token=None,
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.page == 1
    assert result.page_size == 10
    assert result.has_more is False
    assert result.has_prev is False
    assert result.items[0].slug == "gym-alpha"
    assert result.items[0].score and result.items[0].score > 0


@pytest.mark.asyncio
async def test_search_filters_by_required_equipment():
    gym = SimpleNamespace(
        id=1,
        slug="gym-beta",
        name="Gym Beta",
        pref="tokyo",
        city="shibuya",
        last_verified_at_cached=None,
    )

    equipment_row = GymEquipmentSummaryRow(
        gym_id=1,
        slug="bench",
        name="Bench",
        category="strength",
        count=1,
        max_weight_kg=None,
        availability="present",
        verification_status="verified",
        last_verified_at=None,
        source=None,
    )

    repo = FakeGymRepository([gym], [equipment_row])
    service = GymSearchService(lambda: StubUnitOfWork(repo))

    result = await service.search(
        pref=None,
        city=None,
        equipments=["bench"],
        equipment_match="all",
        sort="gym_name",
        page_token=None,
        page=1,
        per_page=5,
    )

    assert result.total == 1
    assert result.page == 1
    assert result.page_size == 5
    assert repo.received_slugs == ["bench"]
