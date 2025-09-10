# tests/fixtures_seed.py
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Equipment, Gym, GymEquipment


@pytest.fixture(scope="session", autouse=True)
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def seed_test_data():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    assert url, "TEST_DATABASE_URL or DATABASE_URL is required for tests"

    engine = create_async_engine(url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async with SessionLocal() as sess:
        exists = await sess.execute(
            Gym.__table__.select().where(Gym.slug == "dummy-funabashi-east")
        )
        if not exists.first():
            g1 = Gym(
                name="ダミージム 船橋イースト",
                slug="dummy-funabashi-east",
                prefecture="chiba",
                city="funabashi",
                address="千葉県船橋市…",
                last_verified_at_cached=datetime.now(UTC) - timedelta(days=30),
            )
            g2 = Gym(
                name="ダミージム 船橋ウエスト",
                slug="dummy-funabashi-west",
                prefecture="chiba",
                city="funabashi",
                address="千葉県船橋市…",
                last_verified_at_cached=None,
            )
            sess.add_all([g1, g2])
            await sess.flush()

            e1 = Equipment(slug="bench-press", name="ベンチプレス", category="free_weight")
            e2 = Equipment(slug="lat-pulldown", name="ラットプルダウン", category="machine")
            sess.add_all([e1, e2])
            await sess.flush()

            sess.add_all(
                [
                    GymEquipment(gym_id=g1.id, equipment_id=e1.id),
                    GymEquipment(gym_id=g1.id, equipment_id=e2.id),
                    GymEquipment(gym_id=g2.id, equipment_id=e1.id),
                ]
            )
            await sess.commit()

    await engine.dispose()
