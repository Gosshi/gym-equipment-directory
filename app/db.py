# app/db.py
import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://appuser:apppass@localhost:5432/gym_directory"
DATABASE_URL = DEFAULT_DATABASE_URL

engine: AsyncEngine
SessionLocal: async_sessionmaker[AsyncSession]


def _create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


def configure_engine(database_url: str | None = None) -> None:
    """Configure SQLAlchemy engine and session factory."""

    global engine, SessionLocal, DATABASE_URL

    DATABASE_URL = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = _create_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_async_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


configure_engine()
