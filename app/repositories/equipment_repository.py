from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment


class EquipmentRepository:
    """Repository for Equipment specific read queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_names(self, q: str, limit: int) -> list[str]:
        if not q:
            return []
        ilike = f"%{q}%"
        stmt: Select = (
            select(Equipment.name)
            .where(Equipment.name.ilike(ilike))
            .order_by(Equipment.name.asc())
            .limit(limit)
        )
        return (await self._session.scalars(stmt)).all()
