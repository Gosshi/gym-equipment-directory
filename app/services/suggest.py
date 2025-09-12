from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.equipment_repository import EquipmentRepository
from app.repositories.gym_repository import GymRepository


class SuggestService:
    """Service for suggestion endpoints (e.g., equipment names)."""

    def __init__(self, session: AsyncSession) -> None:
        self._equip_repo = EquipmentRepository(session)
        self._gym_repo = GymRepository(session)

    async def suggest_equipment_names(self, q: str, limit: int) -> list[str]:
        try:
            return await self._equip_repo.search_names(q, limit)
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def suggest_gyms(self, q: str, pref: str | None, limit: int) -> list[dict]:
        try:
            gyms = await self._gym_repo.suggest_by_name_or_city(q=q, pref=pref, limit=limit)
            return [
                {
                    "slug": g.slug,
                    "name": g.name,
                    "pref": g.pref,
                    "city": g.city,
                }
                for g in gyms
            ]
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")
