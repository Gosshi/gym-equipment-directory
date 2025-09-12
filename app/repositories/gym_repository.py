from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym import Gym


class GymRepository:
    """Repository for Gym model.

    Encapsulates DB access for gyms using Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def get_by_id(self, gym_id: int) -> Gym | None:
        """Fetch a gym by its primary key.

        Args:
            gym_id: Gym.id

        Returns:
            Gym instance if found, otherwise None.
        """
        return await self._session.get(Gym, gym_id)

    async def search_by_name(self, name: str) -> list[Gym]:
        """Search gyms whose name contains the given text (case-insensitive).

        Args:
            name: Partial text to match against `Gym.name`.

        Returns:
            List of matching Gym entities.
        """
        if not name:
            return []

        stmt = select(Gym).where(Gym.name.ilike(f"%{name}%"))
        # scalars() returns ScalarResult[Gym]; .all() -> list[Gym]
        gyms: list[Gym] = (await self._session.scalars(stmt)).all()
        return gyms

    async def list_by_pref_city(self, *, pref: str | None, city: str | None) -> list[Gym]:
        """List gyms filtered by pref and city (case-insensitive equality).

        Args:
            pref: Prefecture slug (lower) or None.
            city: City slug (lower) or None.

        Returns:
            List of Gym entities.
        """
        stmt = select(Gym)
        if pref:
            stmt = stmt.where(func.lower(Gym.pref) == func.lower(pref))
        if city:
            stmt = stmt.where(func.lower(Gym.city) == func.lower(city))
        return (await self._session.scalars(stmt)).all()

    async def get_all_ordered_by_id(self) -> list[Gym]:
        """Return all gyms ordered by id (ascending)."""
        return (await self._session.scalars(select(Gym).order_by(Gym.id))).all()

    async def suggest_by_name_or_city(self, *, q: str, pref: str | None, limit: int) -> list[Gym]:
        """Suggest gyms by partial match on name or city, optionally filtered by pref.

        Args:
            q: Query text (partial, case-insensitive).
            pref: Prefecture slug to filter (case-insensitive) or None.
            limit: Maximum number of results.

        Returns:
            List of Gym entities up to `limit`.
        """
        if not q:
            return []

        stmt = select(Gym).where(Gym.name.ilike(f"%{q}%") | Gym.city.ilike(f"%{q}%"))
        if pref:
            stmt = stmt.where(func.lower(Gym.pref) == func.lower(pref))
        stmt = stmt.limit(int(limit))
        return (await self._session.scalars(stmt)).all()
