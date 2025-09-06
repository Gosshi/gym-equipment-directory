import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_meta_prefs_and_cities():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/meta/prefs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        rc = await ac.get("/meta/cities", params={"pref": "chiba"})
        assert rc.status_code == 200
        assert isinstance(rc.json(), list)

@pytest.mark.asyncio
async def test_search_minimal():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/gyms/search", params={"pref":"chiba","city":"funabashi","per_page":10})
        assert r.status_code == 200
        js = r.json()
        assert "items" in js and "has_next" in js

@pytest.mark.asyncio
async def test_search_richness_any_equipment():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/gyms/search", params={
            "pref":"chiba","city":"funabashi","per_page":10,
            "equipments":"bench-press,dumbbell","equipment_match":"any",
            "sort":"richness"
        })
        assert r.status_code == 200
