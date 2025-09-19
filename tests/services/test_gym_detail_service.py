from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.exceptions import NotFoundError
from app.repositories.interfaces import (
    GymEquipmentBasicRow,
    GymEquipmentSummaryRow,
    GymImageRow,
)
from app.services.gym_detail import GymDetailService


class StubUnitOfWork:
    def __init__(self, gym_repo):
        self.gyms = gym_repo
        self.equipments = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:  # pragma: no cover - not used
        return None

    async def rollback(self) -> None:  # pragma: no cover - not used
        return None


class FakeGymRepository:
    def __init__(self):
        self._gym = SimpleNamespace(
            id=1,
            slug="gym-alpha",
            name="Gym Alpha",
            pref="tokyo",
            city="shibuya",
            updated_at=datetime(2024, 1, 1),
            last_verified_at_cached=datetime(2024, 1, 5),
        )

    async def get_by_slug(self, slug: str):  # noqa: D401
        return self._gym if slug == self._gym.slug else None

    async def fetch_equipment_basic(self, gym_id: int):
        return [
            GymEquipmentBasicRow(
                gym_id=gym_id,
                equipment_slug="rack",
                equipment_name="Power Rack",
                category="strength",
                count=2,
                max_weight_kg=120,
            )
        ]

    async def fetch_equipment_summaries(self, gym_id: int):
        return [
            GymEquipmentSummaryRow(
                gym_id=gym_id,
                slug="rack",
                name="Power Rack",
                category="strength",
                count=2,
                max_weight_kg=120,
                availability="present",
                verification_status="verified",
                last_verified_at=datetime(2024, 1, 3),
                source=None,
            )
        ]

    async def fetch_images(self, gym_id: int):
        return [
            GymImageRow(
                gym_id=gym_id,
                url="https://example.com/rack.jpg",
                source="user",
                verified=True,
                created_at=datetime(2024, 1, 2),
            )
        ]

    async def count_gym_equipments(self, gym_id: int) -> int:
        return 2

    async def max_gym_equipments(self) -> int:
        return 5


@pytest.mark.asyncio
async def test_get_returns_detail_with_scores():
    repo = FakeGymRepository()
    service = GymDetailService(lambda: StubUnitOfWork(repo))

    dto = await service.get("gym-alpha", include="score")

    assert dto.slug == "gym-alpha"
    assert dto.score is not None and dto.freshness is not None
    assert dto.gym_equipments[0].slug == "rack"


@pytest.mark.asyncio
async def test_get_opt_returns_none_when_not_found():
    repo = FakeGymRepository()
    service = GymDetailService(lambda: StubUnitOfWork(repo))

    result = await service.get_opt("missing", include=None)
    assert result is None

    with pytest.raises(NotFoundError):
        await service.get("missing", include=None)
