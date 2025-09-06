import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.main import app
from app.models import Gym, Equipment, GymEquipment
from sqlalchemy import select

@pytest.mark.asyncio
async def test_freshness_paging_has_next_and_end(session):
    # データ準備（2件; tsの降順で g2, g1 の順）
    g1 = Gym(slug="g1", name="G1", pref="chiba", city="funabashi",
             last_verified_at_cached=datetime(2024, 9, 1, 12, 0, 0, tzinfo=None))
    g2 = Gym(slug="g2", name="G2", pref="chiba", city="funabashi",
             last_verified_at_cached=datetime(2024, 9, 2, 12, 0, 0, tzinfo=None))
    session.add_all([g1, g2])
    await session.flush()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1ページ目
        r1 = await ac.get("/gyms/search", params={
            "pref": "chiba", "city": "funabashi", "per_page": 1, "sort": "freshness"
        })
        assert r1.status_code == 200
        b1 = r1.json()
        assert b1["total"] >= 2
        assert b1["has_next"] is True
        assert len(b1["items"]) == 1
        token = b1["page_token"]
        assert token

        # 2ページ目
        r2 = await ac.get("/gyms/search", params={
            "pref": "chiba", "city": "funabashi", "per_page": 1, "sort": "freshness",
            "page_token": token
        })
        assert r2.status_code == 200
        b2 = r2.json()
        assert len(b2["items"]) == 1

        # 終端（has_next False想定）
        if b2.get("page_token"):
            r3 = await ac.get("/gyms/search", params={
                "pref": "chiba", "city": "funabashi", "per_page": 1, "sort": "freshness",
                "page_token": b2["page_token"]
            })
            b3 = r3.json()
            assert b3["has_next"] is False

@pytest.mark.asyncio
async def test_token_sort_mismatch_400(session):
    # 適当なデータ1件
    g = Gym(slug="g3", name="G3", pref="chiba", city="funabashi",
            last_verified_at_cached=datetime(2024, 9, 3, 12, 0, 0))
    session.add(g)
    await session.flush()

    bogus_fresh_token = "eyJzb3J0IjoiZnJlc2huZXNzIiwiayI6W251bGwsMV19"  # {"sort":"freshness","k":[null,1]}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/gyms/search", params={
            "pref":"chiba","city":"funabashi","per_page":1,"sort":"richness","page_token":bogus_fresh_token
        })
        assert r.status_code == 400
        assert r.json()["detail"] == "invalid page_token"

@pytest.mark.asyncio
async def test_richness_paging_and_any_all(session):
    # Equipments
    e_squat = Equipment(slug="squat-rack", name="Squat Rack")
    e_db = Equipment(slug="dumbbell", name="Dumbbell")
    session.add_all([e_squat, e_db])
    await session.flush()

    # Gyms
    g_any = Gym(slug="g-any", name="G Any", pref="chiba", city="funabashi")
    g_all = Gym(slug="g-all", name="G All", pref="chiba", city="funabashi")
    session.add_all([g_any, g_all])
    await session.flush()

    # Link
    session.add_all([
        GymEquipment(gym_id=g_any.id, equipment_id=e_squat.id, count=2, max_weight_kg=100),
        GymEquipment(gym_id=g_all.id, equipment_id=e_squat.id, count=2, max_weight_kg=100),
        GymEquipment(gym_id=g_all.id, equipment_id=e_db.id,    count=1, max_weight_kg=30),
    ])
    await session.flush()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # any: 両方ヒット
        r_any = await ac.get("/gyms/search", params={
            "pref":"chiba","city":"funabashi","equipments":"squat-rack,dumbbell",
            "equipment_match":"any","sort":"richness","per_page":10
        })
        assert r_any.status_code == 200
        names_any = [it["name"] for it in r_any.json()["items"]]
        assert "G Any" in names_any and "G All" in names_any

        # all: dumbbell も持つ g-all のみ
        r_all = await ac.get("/gyms/search", params={
            "pref":"chiba","city":"funabashi","equipments":"squat-rack,dumbbell",
            "equipment_match":"all","sort":"richness","per_page":10
        })
        assert r_all.status_code == 200
        names_all = [it["name"] for it in r_all.json()["items"]]
        assert names_all == ["G All"] or ("G All" in names_all and len(names_all) == 1)
