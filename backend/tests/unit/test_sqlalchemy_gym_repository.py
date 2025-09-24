"""Unit tests for the SQLAlchemy gym repository query helpers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories.interfaces import GymEquipmentSummaryRow
from app.repositories.sqlalchemy.gym import SqlAlchemyGymReadRepository

pytestmark = pytest.mark.unit


class _FakeResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


@pytest.mark.asyncio
async def test_fetch_equipment_for_gyms_converts_enums_and_applies_filters() -> None:
    class Availability(Enum):
        PRESENT = "present"

    class Verification(Enum):
        VERIFIED = "verified"

    session = AsyncMock()
    repo = SqlAlchemyGymReadRepository(session)

    dt = datetime(2024, 6, 1, 9, 0, 0)
    row = SimpleNamespace(
        gym_id=1,
        slug="rack",
        name="Power Rack",
        category="strength",
        availability=Availability.PRESENT,
        verification_status=Verification.VERIFIED,
        last_verified_at=dt,
        count=2,
        max_weight_kg=180.0,
        url="https://example.com",
    )
    session.execute.return_value = _FakeResult([row])

    result = await repo.fetch_equipment_for_gyms(gym_ids=[1, 2], equipment_slugs=["rack"])

    assert result == [
        GymEquipmentSummaryRow(
            gym_id=1,
            slug="rack",
            name="Power Rack",
            category="strength",
            count=2,
            max_weight_kg=180.0,
            availability="present",
            verification_status="verified",
            last_verified_at=dt,
            source="https://example.com",
        )
    ]

    stmt = session.execute.await_args.args[0]
    where_clauses = {str(clause) for clause in stmt._where_criteria}
    assert any("gym_equipments.gym_id" in clause for clause in where_clauses)
    assert any("equipments.slug" in clause for clause in where_clauses)


@pytest.mark.asyncio
async def test_fetch_equipment_for_gyms_skips_query_when_no_ids() -> None:
    session = AsyncMock()
    repo = SqlAlchemyGymReadRepository(session)

    result = await repo.fetch_equipment_for_gyms(gym_ids=[], equipment_slugs=["rack"])

    assert result == []
    session.execute.assert_not_called()
