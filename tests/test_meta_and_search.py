# tests/test_meta_and_search.py

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Equipment, Gym, GymEquipment


@pytest.mark.asyncio
async def test_meta_prefs_and_cities(session):
    # シード
    session.add_all(
        [
            Gym(slug="meta-g1", name="Meta G1", pref="chiba", city="funabashi"),
            Gym(slug="meta-g2", name="Meta G2", pref="chiba", city="urayasu"),
        ]
    )
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/prefs")
        assert r.status_code == 200
        prefs = r.json()
        assert any(p["pref"] == "chiba" for p in prefs)

        r2 = await ac.get("/meta/cities", params={"pref": "chiba"})
        assert r2.status_code == 200
        cities = r2.json()
        assert any(c["city"] == "funabashi" for c in cities)


@pytest.mark.asyncio
async def test_search_minimal(session):
    g = Gym(slug="search-g1", name="Search G1", pref="chiba", city="funabashi")
    session.add(g)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/gyms/search", params={"pref": "chiba", "city": "funabashi", "page_size": 10}
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_search_richness_any_equipment(session):
    e_bp = Equipment(slug="bench-press", name="Bench Press", category="strength")
    e_db = Equipment(slug="dumbbell", name="Dumbbell", category="strength")
    g = Gym(slug="rich-any-2", name="Rich Any 2", pref="chiba", city="funabashi")
    session.add_all([e_bp, e_db, g])
    await session.flush()
    session.add(GymEquipment(gym_id=g.id, equipment_id=e_bp.id, count=1, max_weight_kg=80))
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": "funabashi",
                "page_size": 10,
                "equipments": "bench-press,dumbbell",
                "equipment_match": "any",
                "sort": "richness",
            },
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(it["slug"] == "rich-any-2" for it in items)
