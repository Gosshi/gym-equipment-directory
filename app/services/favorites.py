from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.favorite_repository import FavoriteRepository


class FavoriteService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = FavoriteRepository(session)
        self.session = session

    async def add(self, *, device_id: str, gym_id: int) -> None:
        await self.repo.add(device_id=device_id, gym_id=gym_id)
        await self.session.commit()

    async def list(self, *, device_id: str) -> list[dict]:
        rows = await self.repo.list_with_gym(device_id=device_id)
        out: list[dict] = []
        for fav, gym in rows:
            lv = getattr(gym, "last_verified_at_cached", None)
            lv_str: str | None
            if isinstance(lv, datetime):
                lv_str = lv.isoformat()
            else:
                lv_str = None
            out.append(
                {
                    "gym_id": int(getattr(gym, "id", 0)),
                    "slug": str(getattr(gym, "slug", "")),
                    "name": str(getattr(gym, "name", "")),
                    "pref": str(getattr(gym, "pref", "")),
                    "city": str(getattr(gym, "city", "")),
                    "last_verified_at": lv_str,
                }
            )
        return out

    async def remove(self, *, device_id: str, gym_id: int) -> None:
        await self.repo.remove(device_id=device_id, gym_id=gym_id)
        await self.session.commit()
