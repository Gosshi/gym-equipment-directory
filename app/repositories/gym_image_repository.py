from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym_image import GymImage


class GymImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_gym_id(self, gym_id: int) -> list[GymImage]:
        stmt = (
            select(GymImage)
            .where(GymImage.gym_id == gym_id)
            .order_by(GymImage.created_at.desc(), GymImage.id.desc())
        )
        return (await self._session.scalars(stmt)).all()
