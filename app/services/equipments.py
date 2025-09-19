from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto import EquipmentMasterDTO
from app.dto.mappers import map_equipment_master
from app.models import Equipment


class EquipmentService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, q: str | None, limit: int) -> list[EquipmentMasterDTO]:
        try:
            stmt = select(Equipment.id, Equipment.slug, Equipment.name, Equipment.category)
            if q:
                ilike = f"%{q}%"
                stmt = stmt.where(or_(Equipment.slug.ilike(ilike), Equipment.name.ilike(ilike)))
            stmt = stmt.order_by(Equipment.slug.asc()).limit(limit)
            rows = await self._session.execute(stmt)
            return [map_equipment_master(r) for r in rows.mappings()]
        except SQLAlchemyError:
            # Unify DB errors as 503
            raise HTTPException(status_code=503, detail="database unavailable")
