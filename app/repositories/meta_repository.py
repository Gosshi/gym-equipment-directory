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

    async def list_equipment_options(self) -> list[dict[str, str | None]]:
        stmt: Select = (
            select(
                Equipment.slug.label("slug"),
                Equipment.name.label("name"),
                Equipment.category.label("category"),
            )
            .where(Equipment.slug.is_not(None), Equipment.slug != "")
            .order_by(Equipment.name.asc(), Equipment.slug.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        results: list[dict[str, str | None]] = []
        seen: set[str] = set()
        for row in rows:
            slug = row.get("slug")
            name = row.get("name")
            if not slug or slug in seen:
                continue
            seen.add(slug)
            results.append(
                {
                    "slug": slug,
                    "name": name or slug,
                    "category": row.get("category"),
                }
            )
        return results
