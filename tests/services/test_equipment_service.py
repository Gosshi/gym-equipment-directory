from __future__ import annotations

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import InfrastructureError
from app.repositories.interfaces import EquipmentMasterRow
from app.services.equipments import EquipmentService


class StubUnitOfWork:
    def __init__(self, equipment_repo):
        self.gyms = None
        self.equipments = equipment_repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:  # pragma: no cover - not used
        return None

    async def rollback(self) -> None:  # pragma: no cover - not used
        return None


class FakeEquipmentRepository:
    def __init__(self, rows):
        self._rows = rows

    async def search(self, *, q, limit):  # noqa: D401
        return self._rows[:limit]


@pytest.mark.asyncio
async def test_list_returns_dtos():
    rows = [
        EquipmentMasterRow(id=1, slug="rack", name="Power Rack", category="strength"),
        EquipmentMasterRow(id=2, slug="bench", name="Bench Press", category="strength"),
    ]
    repo = FakeEquipmentRepository(rows)
    service = EquipmentService(lambda: StubUnitOfWork(repo))

    result = await service.list(q=None, limit=1)

    assert len(result) == 1
    assert result[0].slug == "rack"


class FailingEquipmentRepository:
    async def search(self, *, q, limit):  # noqa: D401
        raise SQLAlchemyError("db error")


@pytest.mark.asyncio
async def test_list_raises_infrastructure_error_on_failure():
    repo = FailingEquipmentRepository()
    service = EquipmentService(lambda: StubUnitOfWork(repo))

    with pytest.raises(InfrastructureError):
        await service.list(q=None, limit=10)
