# app/db.py
import os

from sqlalchemy.engine.url import make_url
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


def _apply_asyncpg_scheme(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


def _create_engine(database_url: str) -> AsyncEngine:
    url = make_url(database_url)
    connect_args = {}

    # Handle sslmode for asyncpg
    if url.get_backend_name() == "postgresql" and url.get_driver_name() == "asyncpg":
        query = dict(url.query)
        if "sslmode" in query:
            # asyncpg accepts 'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'
            connect_args["ssl"] = query.pop("sslmode")

        if "channel_binding" in query:
            # asyncpg does not support channel_binding, so we remove it
            query.pop("channel_binding")

        # Reconstruct URL without sslmode and channel_binding
        url = url._replace(query=query)

    return create_async_engine(
        url,
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )


def configure_engine(database_url: str | None = None) -> None:
    """Configure SQLAlchemy engine and session factory."""

    global engine, SessionLocal, DATABASE_URL

    DATABASE_URL = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    normalized_database_url = _apply_asyncpg_scheme(DATABASE_URL)
    engine = _create_engine(normalized_database_url)
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
