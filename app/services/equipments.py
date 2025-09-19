"""Equipment master queries using the repository abstraction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import InfrastructureError
from app.dto import EquipmentMasterDTO
from app.dto.mappers import map_equipment_master
from app.infra.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]


class EquipmentService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, q: str | None, limit: int) -> list[EquipmentMasterDTO]:
        try:
            async with self._uow_factory() as uow:
                rows = await uow.equipments.search(q=q, limit=limit)
                return [map_equipment_master(asdict(row)) for row in rows]
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            raise InfrastructureError("database unavailable") from exc
