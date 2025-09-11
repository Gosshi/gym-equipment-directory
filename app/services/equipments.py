from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment


class EquipmentMaster(BaseModel):
    id: int = Field(description="設備ID")
    slug: str = Field(description="スラッグ（lower-case, kebab）")
    name: str = Field(description="表示名")
    category: str | None = Field(None, description="カテゴリ（任意）")


class EquipmentService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, q: str | None, limit: int) -> list[EquipmentMaster]:
        try:
            stmt = select(Equipment.id, Equipment.slug, Equipment.name, Equipment.category)
            if q:
                ilike = f"%{q}%"
                stmt = stmt.where(or_(Equipment.slug.ilike(ilike), Equipment.name.ilike(ilike)))
            stmt = stmt.order_by(Equipment.slug.asc()).limit(limit)
            rows = await self._session.execute(stmt)
            return [EquipmentMaster.model_validate(dict(r)) for r in rows.mappings()]
        except SQLAlchemyError:
            # Unify DB errors as 503
            raise HTTPException(status_code=503, detail="database unavailable")
