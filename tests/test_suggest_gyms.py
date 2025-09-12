import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_suggest_gyms_basic(app_client: AsyncClient):
    # Japanese partial match on name (seed contains 船橋 in name)
    r = await app_client.get("/suggest/gyms", params={"q": "船橋"})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert all(set(["slug", "name", "pref", "city"]).issubset(i.keys()) for i in items)
    assert any("船橋" in i["name"] for i in items)

    # limit behavior
    r2 = await app_client.get("/suggest/gyms", params={"q": "ダミー", "limit": 1})
    assert r2.status_code == 200
    items2 = r2.json()
    assert len(items2) <= 1


@pytest.mark.asyncio
async def test_suggest_gyms_romaji_city_match(app_client: AsyncClient):
    # Romaji city slug should match on gyms.city
    r = await app_client.get("/suggest/gyms", params={"q": "funabashi"})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(i["city"] == "funabashi" for i in items)


@pytest.mark.asyncio
async def test_suggest_gyms_empty(app_client: AsyncClient):
    r = await app_client.get("/suggest/gyms", params={"q": "zzz-not-found"})
    assert r.status_code == 200
    assert r.json() == []
