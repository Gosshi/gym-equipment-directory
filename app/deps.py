from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session


async def get_db() -> AsyncSession:
    async for s in get_async_session():
        yield s
