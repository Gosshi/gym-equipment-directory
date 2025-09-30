from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.models import Base, GymCandidate, ScrapedPage, Source
from app.models.gym_candidate import CandidateStatus
from app.models.source import SourceType


def _database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL must be set for DB schema tests")
    if not url.startswith(("postgresql+asyncpg://", "postgresql+psycopg://")):
        pytest.skip("Database URL must point to a PostgreSQL instance for schema tests")
    return url


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    from sqlalchemy.exc import SQLAlchemyError

    db_url = _database_url()
    async_engine = create_async_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )

    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("SET search_path TO public"))
            await conn.run_sync(Base.metadata.create_all)
    except (OSError, SQLAlchemyError) as exc:  # pragma: no cover - env dependent
        await async_engine.dispose()
        pytest.skip(f"PostgreSQL database not available: {exc}")

    try:
        yield async_engine
    finally:
        await async_engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with SessionLocal() as db_session:
        yield db_session
        if db_session.in_transaction():
            await db_session.rollback()


@pytest.mark.asyncio
async def test_candidate_creation_and_relationship(session: AsyncSession) -> None:
    source = Source(
        source_type=SourceType.official_site,
        title="Example Site",
        url="https://example.com",
    )
    session.add(source)
    await session.flush()

    page = ScrapedPage(
        source_id=source.id,
        url="https://example.com/gym",
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="a" * 64,
        raw_html="<html></html>",
    )
    session.add(page)
    await session.flush()

    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw="Example Gym",
        address_raw="東京都新宿区",
        pref_slug="tokyo",
        city_slug="shinjuku",
        latitude=35.6895,
        longitude=139.6917,
        parsed_json={"equipments": ["smith-machine"]},
    )
    session.add(candidate)
    await session.commit()

    stmt = (
        select(GymCandidate)
        .options(selectinload(GymCandidate.source_page))
        .where(GymCandidate.id == candidate.id)
    )
    stored = (await session.execute(stmt)).scalar_one()

    assert stored.status is CandidateStatus.new
    assert stored.parsed_json == {"equipments": ["smith-machine"]}
    assert stored.source_page_id == page.id
    assert stored.source_page.id == page.id

    page_stmt = (
        select(ScrapedPage)
        .options(selectinload(ScrapedPage.candidates))
        .where(ScrapedPage.id == page.id)
    )
    page_fetched = (await session.execute(page_stmt)).scalar_one()
    assert {c.id for c in page_fetched.candidates} == {stored.id}


@pytest.mark.asyncio
async def test_candidate_indexes_and_enum(session: AsyncSession) -> None:
    enum_result = await session.execute(text("SELECT enum_range(NULL::candidate_status)"))
    (enum_values,) = enum_result.one()
    assert "new" in enum_values

    index_rows = await session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'scraped_pages'")
    )
    index_names = {row.indexname for row in index_rows}
    assert "ix_scraped_pages_fetched_at_desc" in index_names
    assert "ix_scraped_pages_content_hash" in index_names

    candidate_index_rows = await session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'gym_candidates'")
    )
    candidate_index_names = {row.indexname for row in candidate_index_rows}
    expected_indexes = {
        "ix_gym_candidates_status",
        "ix_gym_candidates_pref_city",
        "ix_gym_candidates_parsed_json",
    }
    assert expected_indexes.issubset(candidate_index_names)
