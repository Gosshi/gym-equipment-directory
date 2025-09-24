"""Lightweight dataset seeding utility for integration tests."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.gym import Gym

MINIMAL_GYM_DATASET: Final[list[dict[str, object]]] = [
    {
        "name": "Integration Hub Gym",
        "slug": "integration-hub-gym",
        "pref": "tokyo",
        "city": "shibuya",
        "address": "1-2-3 Integration Ave, Shibuya-ku, Tokyo",
        "latitude": 35.6595,
        "longitude": 139.7005,
        "last_verified_at_cached": datetime(2024, 5, 1, tzinfo=UTC),
    },
    {
        "name": "Integration Riverside Gym",
        "slug": "integration-riverside-gym",
        "pref": "tokyo",
        "city": "shibuya",
        "address": "4-5-6 Riverside Road, Shibuya-ku, Tokyo",
        "latitude": 35.658,
        "longitude": 139.702,
        "last_verified_at_cached": datetime(2024, 4, 10, tzinfo=UTC),
    },
    {
        "name": "Integration West Gym",
        "slug": "integration-west-gym",
        "pref": "tokyo",
        "city": "shibuya",
        "address": "7-8-9 West Street, Shibuya-ku, Tokyo",
        "latitude": 35.657,
        "longitude": 139.695,
        "last_verified_at_cached": datetime(2024, 3, 5, tzinfo=UTC),
    },
]


async def seed_minimal_dataset(*, database_url: str | None = None) -> None:
    """Replace the gyms table contents with a deterministic minimal dataset."""
    url = database_url or os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set for seeding")

    print(f"[seed_min_test] Using database URL: {url}")
    engine = create_async_engine(url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        await _seed_gyms(session)

    await engine.dispose()
    print("[seed_min_test] Seeded minimal gyms dataset")


async def _seed_gyms(session: AsyncSession) -> None:
    """Clear gyms and insert the minimal dataset."""
    print("[seed_min_test] Clearing gyms table")
    async with session.begin():
        await session.execute(delete(Gym))
        for payload in MINIMAL_GYM_DATASET:
            session.add(Gym(**payload))

    total = await session.scalar(select(func.count()).select_from(Gym))
    print(f"[seed_min_test] gyms table now contains {int(total or 0)} rows")


async def _async_main() -> None:
    await seed_minimal_dataset()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
