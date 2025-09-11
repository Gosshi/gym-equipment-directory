from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def ok(self) -> dict:
        await self._session.execute(text("SELECT 1"))
        return {"ok": True}

