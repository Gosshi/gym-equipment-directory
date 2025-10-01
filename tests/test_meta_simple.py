import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Gym
from app.services.canonical import make_canonical_id


@pytest.mark.asyncio
async def test_meta_prefectures_and_categories(session):
    # extra seed to ensure multiple values
    session.add(
        Gym(
            slug="meta-x",
            name="Meta X",
            canonical_id=make_canonical_id("tokyo", "shinjuku", "Meta X"),
            pref="tokyo",
            city="shinjuku",
        )
    )
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/meta/prefectures")
        assert r1.status_code == 200
        prefs = r1.json()
        assert isinstance(prefs, list)
        assert "chiba" in prefs
        assert "tokyo" in prefs

        r2 = await ac.get("/meta/equipment-categories")
        assert r2.status_code == 200
        cats = r2.json()
        assert isinstance(cats, list)
        # seeded categories from tests/conftest.py
        assert "free_weight" in cats
        assert "machine" in cats


@pytest.mark.asyncio
async def test_meta_prefectures_empty(session):
    # clear gyms to force empty result
    await session.execute(Gym.__table__.delete())
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/meta/prefectures")
        assert r.status_code == 200
        assert r.json() == []
