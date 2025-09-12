from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.equipment_repository import EquipmentRepository


class SuggestService:
    """Service for suggestion endpoints (e.g., equipment names)."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = EquipmentRepository(session)

    async def suggest_equipment_names(self, q: str, limit: int) -> list[str]:
        try:
            return await self._repo.search_names(q, limit)
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")
