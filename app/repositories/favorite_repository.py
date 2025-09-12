from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import Favorite
from app.models.gym import Gym


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, *, device_id: str, gym_id: int) -> None:
        """Idempotent insert using ON CONFLICT DO NOTHING."""
        stmt = (
            insert(Favorite)
            .values(device_id=device_id, gym_id=int(gym_id))
            .on_conflict_do_nothing(index_elements=[Favorite.device_id, Favorite.gym_id])
        )
        await self._session.execute(stmt)

    async def list_with_gym(self, *, device_id: str) -> list[tuple[Favorite, Gym]]:
        stmt = (
            select(Favorite, Gym)
            .join(Gym, Gym.id == Favorite.gym_id)
            .where(Favorite.device_id == device_id)
            .order_by(Favorite.created_at.desc(), Favorite.gym_id.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        return list(rows)

    async def remove(self, *, device_id: str, gym_id: int) -> None:
        stmt = delete(Favorite).where(
            Favorite.device_id == device_id, Favorite.gym_id == int(gym_id)
        )
        await self._session.execute(stmt)
