import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_suggest_equipments_basic(app_client: AsyncClient):
    # uses seeded equipments (ベンチプレス, ラットプルダウン)
    r = await app_client.get("/suggest/equipments", params={"q": "ベンチ"})
    assert r.status_code == 200
    names = r.json()
    assert isinstance(names, list)
    assert any("ベンチ" in n for n in names)

    r2 = await app_client.get("/suggest/equipments", params={"q": "ラット", "limit": 1})
    assert r2.status_code == 200
    names2 = r2.json()
    assert len(names2) <= 1


@pytest.mark.asyncio
async def test_suggest_equipments_empty(app_client: AsyncClient):
    r = await app_client.get("/suggest/equipments", params={"q": "zzz-not-found"})
    assert r.status_code == 200
    assert r.json() == []
