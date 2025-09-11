from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gym


class MetaService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_prefs(self) -> list[dict]:
        try:
            stmt = (
                select(
                    Gym.pref.label("pref"),
                    func.count().label("count"),
                )
                .where(Gym.pref != "")
                .group_by(Gym.pref)
                .order_by(func.count().desc(), Gym.pref.asc())
            )
            rows = (await self._session.execute(stmt)).mappings().all()
            return [{"pref": r["pref"], "count": int(r["count"])} for r in rows]
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_cities(self, pref: str) -> list[dict]:
        try:
            pref_norm = pref.lower()

            exists_count = await self._session.scalar(
                select(func.count()).select_from(Gym).where(Gym.pref == pref_norm)
            )
            if not exists_count:
                raise HTTPException(status_code=404, detail="pref not found")

            stmt = (
                select(
                    Gym.city.label("city"),
                    func.count().label("count"),
                )
                .where(Gym.pref == pref_norm, Gym.city != "")
                .group_by(Gym.city)
                .order_by(func.count().desc(), Gym.city.asc())
            )
            rows = (await self._session.execute(stmt)).mappings().all()
            return [{"city": r["city"], "count": int(r["count"])} for r in rows]
        except HTTPException:
            raise
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")
