from __future__ import annotations

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym


class MetaRepository:
    """Read-only repository for fetching distinct metadata values."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_distinct_prefs(self) -> list[str]:
        stmt: Select = (
            select(distinct(Gym.pref))
            .where(Gym.pref.is_not(None), Gym.pref != "")
            # Postgres では DISTINCT 時の ORDER BY は選択列に限定されるため lower() は使わない
            .order_by(Gym.pref.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [p for p in rows if p]

    async def list_distinct_cities(self, pref: str) -> list[str]:
        stmt: Select = (
            select(distinct(Gym.city))
            .where(
                func.lower(Gym.pref) == func.lower(pref),
                Gym.city.is_not(None),
                Gym.city != "",
            )
            .order_by(Gym.city.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [c for c in rows if c]

    async def list_distinct_equipment_categories(self) -> list[str]:
        stmt: Select = (
            select(distinct(Equipment.category))
            .where(Equipment.category.is_not(None), Equipment.category != "")
            .order_by(Equipment.category.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [c for c in rows if c]
