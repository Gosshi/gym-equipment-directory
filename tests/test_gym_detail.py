import pytest
from httpx import AsyncClient
from datetime import datetime

from app.main import app
from app.models import Gym, Equipment, GymEquipment

@pytest.mark.asyncio
async def test_gym_detail_fields(session):
    g = Gym(slug="tokyo-x", name="Tokyo X", pref="tokyo", city="chiyoda",
            last_verified_at_cached=datetime(2024, 8, 1, 10, 0, 0))
    e = Equipment(slug="smith-machine", name="Smith Machine")
    session.add_all([g, e])
    await session.flush()
    session.add(GymEquipment(gym_id=g.id, equipment_id=e.id, count=1, max_weight_kg=80))
    await session.flush()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/gyms/tokyo-x")
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "tokyo-x"
        assert body["pref"] == "tokyo"
        assert body["city"] == "chiyoda"
        assert isinstance(body.get("equipments"), list)
        eq = body["equipments"][0]
        assert eq["equipment_slug"] == "smith-machine"
        assert "count" in eq and "max_weight_kg" in eq
