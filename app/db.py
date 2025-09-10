# app/db.py
import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Lazily create engine/sessionmaker so tests can replace DATABASE_URL and avoid
# creating asyncpg connections bound to the wrong event loop at import time.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://appuser:apppass@localhost:5432/gym_directory"
)

# module-level placeholders (may be replaced by test fixtures)
engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker | None = None


def _ensure_engine_and_sessionmaker():
    global engine, SessionLocal
    if engine is None or SessionLocal is None:
        url = os.getenv("DATABASE_URL", DATABASE_URL)
        engine = create_async_engine(url, pool_pre_ping=True, future=True)
        SessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )


async def get_async_session() -> AsyncSession:
    _ensure_engine_and_sessionmaker()
    assert SessionLocal is not None
    async with SessionLocal() as session:
        yield session
