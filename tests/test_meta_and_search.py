# tests/test_meta_and_search.py

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Equipment, Gym, GymEquipment
from app.services.canonical import make_canonical_id


@pytest.mark.asyncio
async def test_meta_prefs_and_cities(session):
    # シード
    session.add_all(
        [
            Gym(
                slug="meta-g1",
                name="Meta G1",
                canonical_id=make_canonical_id("chiba", "funabashi", "Meta G1"),
                pref="chiba",
                city="funabashi",
            ),
            Gym(
                slug="meta-g2",
                name="Meta G2",
                canonical_id=make_canonical_id("chiba", "urayasu", "Meta G2"),
                pref="chiba",
                city="urayasu",
            ),
        ]
    )
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/prefs")
        assert r.status_code == 200
        prefs = r.json()
        assert any(p["key"] == "chiba" and p["label"] == "chiba" for p in prefs)
        assert all("count" in p for p in prefs)

        r2 = await ac.get("/meta/cities", params={"pref": "chiba"})
        assert r2.status_code == 200
        cities = r2.json()
        assert any(c["key"] == "funabashi" and c["label"] == "funabashi" for c in cities)

        # 互換: prefecture パラメータでも取得可能
        r3 = await ac.get("/meta/cities", params={"prefecture": "chiba"})
        assert r3.status_code == 200
        cities2 = r3.json()
        assert any(c["key"] == "urayasu" for c in cities2)


@pytest.mark.asyncio
async def test_meta_equipments(session):
    e1 = Equipment(slug="smith-machine", name="Smith Machine", category="strength")
    e2 = Equipment(slug="leg-press", name="Leg Press", category="machine")
    session.add_all([e1, e2])
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/equipments")
        assert r.status_code == 200
        equipments = r.json()
        slugs = {item["key"] for item in equipments}
        assert "smith-machine" in slugs


@pytest.mark.asyncio
async def test_meta_categories(session):
    e1 = Equipment(slug="smith-machine", name="Smith Machine", category="strength")
    session.add(e1)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/equipment-categories")
        assert r.status_code == 200
        categories = r.json()
        assert any(c["key"] == "strength" and c["label"] == "strength" for c in categories)
        assert all("count" in c for c in categories)


@pytest.mark.asyncio
async def test_search_minimal(session):
    g = Gym(
        slug="search-g1",
        name="Search G1",
        canonical_id=make_canonical_id("chiba", "funabashi", "Search G1"),
        pref="chiba",
        city="funabashi",
    )
    session.add(g)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/gyms/search", params={"pref": "chiba", "city": "funabashi", "page_size": 10}
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

        # 互換: prefecture パラメータ
        r2 = await ac.get(
            "/gyms/search", params={"prefecture": "chiba", "city": "funabashi", "page_size": 10}
        )
        assert r2.status_code == 200
        assert r2.json()["total"] >= 1


@pytest.mark.asyncio
async def test_search_richness_any_equipment(session):
    e_bp = Equipment(slug="bench-press", name="Bench Press", category="strength")
    e_db = Equipment(slug="dumbbell", name="Dumbbell", category="strength")
    g = Gym(
        slug="rich-any-2",
        name="Rich Any 2",
        canonical_id=make_canonical_id("chiba", "funabashi", "Rich Any 2"),
        pref="chiba",
        city="funabashi",
    )
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


@pytest.mark.asyncio
async def test_meta_cities_handles_not_found_and_validation(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/cities", params={"pref": "unknown-pref"})
        assert r.status_code == 404
        assert r.json()["detail"] == "pref not found"

        invalid = await ac.get("/meta/cities", params={"pref": "Invalid"})
        assert invalid.status_code == 422
        assert invalid.json()["detail"] == "Unprocessable Entity"

        invalid2 = await ac.get("/meta/cities", params={"prefecture": "Invalid"})
        assert invalid2.status_code == 422
        assert invalid2.json()["detail"] == "Unprocessable Entity"


@pytest.mark.asyncio
async def test_meta_categories_new(session):
    # categories エンドポイント互換確認
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/meta/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_meta_cache_population(session):
    # キャッシュ: prefectures を複数回叩いて同一結果を期待
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get("/meta/prefectures")
        assert r1.status_code == 200
        data1 = r1.json()
        r2 = await ac.get("/meta/prefectures")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data1 == data2


@pytest.mark.asyncio
async def test_search_validation_error_returns_422(app_client):
    r = await app_client.get(
        "/gyms/search",
        params={"pref": "chiba", "city": "funabashi", "page_size": 1000},
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "Unprocessable Entity"
