"""SQLAlchemy implementation of equipment repository."""

from __future__ import annotations

from app.models import Equipment
from app.repositories.interfaces import EquipmentMasterRow, EquipmentReadRepository
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyEquipmentReadRepository(EquipmentReadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, *, q: str | None, limit: int) -> list[EquipmentMasterRow]:
        stmt = select(Equipment.id, Equipment.slug, Equipment.name, Equipment.category)
        if q:
            ilike = f"%{q}%"
            stmt = stmt.where(or_(Equipment.slug.ilike(ilike), Equipment.name.ilike(ilike)))
        stmt = stmt.order_by(Equipment.slug.asc()).limit(limit)

        rows = await self._session.execute(stmt)
        return [
            EquipmentMasterRow(
                id=row.id,
                slug=row.slug,
                name=row.name,
                category=row.category,
            )
            for row in rows.all()
        ]
