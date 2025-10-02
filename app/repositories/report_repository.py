from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym import Gym
from app.models.gym_slug import GymSlug
from app.models.report import Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_gym_by_slug(self, slug: str) -> Gym | None:
        stmt = select(Gym).where(Gym.slug == slug)
        gym = (await self._session.scalars(stmt)).first()
        if gym:
            return gym
        stmt = select(Gym).join(GymSlug, GymSlug.gym_id == Gym.id).where(GymSlug.slug == slug)
        return (await self._session.scalars(stmt)).first()

    async def create(
        self, *, gym_id: int, type: str, message: str, email: str | None, source_url: str | None
    ) -> Report:
        r = Report(gym_id=gym_id, type=type, message=message, email=email, source_url=source_url)
        self._session.add(r)
        await self._session.flush()
        return r

    async def list_by_status_keyset(
        self, *, status: str, limit: int, cursor: tuple[datetime, int] | None
    ) -> tuple[list[tuple[Report, Gym]], tuple[datetime, int] | None]:
        # keyset on (created_at DESC, id DESC). Join gyms for slug display.
        stmt = select(Report, Gym).join(Gym, Gym.id == Report.gym_id).where(Report.status == status)
        if cursor:
            cts, cid = cursor
            stmt = stmt.where(tuple_(Report.created_at, Report.id) < tuple_(cts, int(cid)))
        stmt = stmt.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit + 1)
        rows = (await self._session.execute(stmt)).all()
        items = list(rows)[:limit]
        next_cursor: tuple[datetime, int] | None = None
        if len(rows) > limit and items:
            last_r, _ = items[-1]
            next_cursor = (last_r.created_at, int(last_r.id))
        return items, next_cursor

    async def resolve(self, report_id: int) -> Report | None:
        r = await self._session.get(Report, report_id)
        if not r:
            return None
        r.status = "resolved"
        await self._session.flush()
        return r
