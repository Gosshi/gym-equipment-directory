# tests/test_gym_detail.py
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Equipment, Gym, GymEquipment
from app.services.canonical import make_canonical_id


@pytest.mark.asyncio
async def test_gym_detail_fields(session):
    g = Gym(
        slug="tokyo-x",
        name="Tokyo X",
        canonical_id=make_canonical_id("tokyo", "chiyoda", "Tokyo X"),
        pref="tokyo",
        city="chiyoda",
        last_verified_at_cached=datetime(2024, 8, 1, 10, 0, 0),
    )
    e = Equipment(slug="smith-machine", name="Smith Machine", category="machine")
    session.add_all([g, e])
    await session.flush()
    session.add(GymEquipment(gym_id=g.id, equipment_id=e.id, count=1, max_weight_kg=80))
    await session.commit()  # ← APIは別セッションなので commit が必要

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/gyms/tokyo-x")
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "tokyo-x"
        assert body["pref"] == "tokyo"
        assert body["city"] == "chiyoda"
        assert body["canonical_id"] == g.canonical_id
        assert body["last_verified_at_cached"].startswith("2024-08-01T10:00:00")
        assert body["last_verified_at"] == body["last_verified_at_cached"]
        eq = body["equipments"][0]
        assert eq["equipment_slug"] == "smith-machine"
        assert eq["slug"] == "smith-machine"
        assert eq["name"] == "Smith Machine"
        assert eq["category"] == "machine"
        assert eq["description"] == "1台 / 最大80kg"
        assert "count" in eq and "max_weight_kg" in eq
        detail_eq = body["equipment_details"][0]
        assert detail_eq["name"] == "Smith Machine"


@pytest.mark.asyncio
async def test_gym_detail_invalid_include_returns_422(app_client):
    r = await app_client.get("/gyms/dummy-funabashi-east", params={"include": "score,all"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Unprocessable Entity"


@pytest.mark.asyncio
async def test_gym_detail_returns_placeholders_when_missing(app_client, session):
    slug = "empty-gym-detail"
    g = Gym(
        slug=slug,
        name="Empty Gym",
        canonical_id=make_canonical_id("tokyo", "adachi", "Empty Gym"),
        pref="tokyo",
        city="adachi",
        last_verified_at_cached=None,
    )
    session.add(g)
    await session.commit()

    resp = await app_client.get(f"/gyms/{slug}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["equipments"] == []
    assert body["gym_equipments"] == []
    assert body["images"] == []
    assert body["last_verified_at_cached"] is None


@pytest.mark.anyio
async def test_gym_detail_sorts_equipments(app_client, session):
    slug = "sorted-gym-detail"
    gym = Gym(
        slug=slug,
        name="Sorted Gym",
        canonical_id=make_canonical_id("tokyo", "chuo", "Sorted Gym"),
        pref="tokyo",
        city="chuo",
    )
    eq1 = Equipment(slug="b-machine", name="B Machine", category="machine")
    eq2 = Equipment(slug="a-free", name="A Free", category="free_weight")
    eq3 = Equipment(slug="c-unknown", name="C Unknown", category=None)
    session.add_all([gym, eq1, eq2, eq3])
    await session.flush()

    session.add_all(
        [
            GymEquipment(gym_id=gym.id, equipment_id=eq1.id, count=1),
            GymEquipment(gym_id=gym.id, equipment_id=eq2.id, count=2),
            GymEquipment(gym_id=gym.id, equipment_id=eq3.id, count=3),
        ]
    )
    await session.commit()

    resp = await app_client.get(f"/gyms/{slug}")
    assert resp.status_code == 200
    payload = resp.json()

    equipments = payload["equipments"]
    assert [
        (item["category"], item["equipment_name"], item["equipment_slug"])
        for item in equipments
    ] == [
        ("free_weight", "A Free", "a-free"),
        ("machine", "B Machine", "b-machine"),
        (None, "C Unknown", "c-unknown"),
    ]

    gym_equipments = payload["gym_equipments"]
    assert [
        (item.get("category"), item["name"], item["slug"])
        for item in gym_equipments
    ] == [
        ("free_weight", "A Free", "a-free"),
        ("machine", "B Machine", "b-machine"),
        (None, "C Unknown", "c-unknown"),
    ]
