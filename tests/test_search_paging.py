# tests/test_search_paging.py
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Equipment, Gym, GymEquipment
from app.services.canonical import make_canonical_id


@pytest.mark.asyncio
async def test_freshness_paging_has_next_and_end(session):
    # シードで city="funabashi" のジムが既に2件投入されているため
    # 本テストはデータ件数=2 の前提を崩さないよう、衝突しない別 city を使用する
    test_city = "funabashi2"
    g1 = Gym(
        slug="g1",
        name="G1",
        canonical_id=make_canonical_id("chiba", test_city, "G1"),
        pref="chiba",
        city=test_city,
        last_verified_at_cached=datetime(2024, 9, 1, 12, 0, 0),
    )
    g2 = Gym(
        slug="g2",
        name="G2",
        canonical_id=make_canonical_id("chiba", test_city, "G2"),
        pref="chiba",
        city=test_city,
        last_verified_at_cached=datetime(2024, 9, 2, 12, 0, 0),
    )
    session.add_all([g1, g2])
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": test_city,
                "page_size": 1,
                "sort": "freshness",
            },
        )
        assert r1.status_code == 200
        b1 = r1.json()
        assert b1["has_more"] is True
        assert b1["page"] == 1

        r2 = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": test_city,
                "page_size": 1,
                "sort": "freshness",
                "page": 2,
            },
        )
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["page"] == 2

        if b2.get("has_more"):
            r3 = await ac.get(
                "/gyms/search",
                params={
                    "pref": "chiba",
                    "city": test_city,
                    "page_size": 1,
                    "sort": "freshness",
                    "page": 3,
                },
            )
            b3 = r3.json()
            assert b3["has_more"] is False


@pytest.mark.asyncio
async def test_token_sort_mismatch_422(session):
    g = Gym(
        slug="g3",
        name="G3",
        canonical_id=make_canonical_id("chiba", "funabashi", "G3"),
        pref="chiba",
        city="funabashi",
        last_verified_at_cached=datetime(2024, 9, 3, 12, 0, 0),
    )
    session.add(g)
    await session.commit()

    bogus_fresh_token = (
        "eyJzb3J0IjoiZnJlc2huZXNzIiwiayI6W251bGwsMV19"  # {"sort":"freshness","k":[null,1]}
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": "funabashi",
                "page_size": 1,
                "sort": "richness",
                "page_token": bogus_fresh_token,
            },
        )
        assert r.status_code == 422
        assert r.json()["detail"] == "invalid page_token"


@pytest.mark.asyncio
async def test_richness_paging_and_any_all(session):
    # Equipments with category (NOT NULL)
    e_squat = Equipment(slug="squat-rack", name="Squat Rack", category="strength")
    e_db = Equipment(slug="dumbbell", name="Dumbbell", category="strength")
    session.add_all([e_squat, e_db])
    await session.flush()

    g_any = Gym(
        slug="g-any",
        name="G Any",
        canonical_id=make_canonical_id("chiba", "funabashi", "G Any"),
        pref="chiba",
        city="funabashi",
    )
    g_all = Gym(
        slug="g-all",
        name="G All",
        canonical_id=make_canonical_id("chiba", "funabashi", "G All"),
        pref="chiba",
        city="funabashi",
    )
    session.add_all([g_any, g_all])
    await session.flush()

    session.add_all(
        [
            GymEquipment(gym_id=g_any.id, equipment_id=e_squat.id, count=2, max_weight_kg=100),
            GymEquipment(gym_id=g_all.id, equipment_id=e_squat.id, count=2, max_weight_kg=100),
            GymEquipment(gym_id=g_all.id, equipment_id=e_db.id, count=1, max_weight_kg=30),
        ]
    )
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_any = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": "funabashi",
                "equipments": "squat-rack,dumbbell",
                "equipment_match": "any",
                "sort": "richness",
                "page_size": 10,
            },
        )
        assert r_any.status_code == 200
        names_any = [it["name"] for it in r_any.json()["items"]]
        assert "G Any" in names_any and "G All" in names_any

        r_all = await ac.get(
            "/gyms/search",
            params={
                "pref": "chiba",
                "city": "funabashi",
                "equipments": "squat-rack,dumbbell",
                "equipment_match": "all",
                "sort": "richness",
                "page_size": 10,
            },
        )
        assert r_all.status_code == 200
        names_all = [it["name"] for it in r_all.json()["items"]]
        assert names_all == ["G All"] or ("G All" in names_all and len(names_all) == 1)
