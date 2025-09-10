import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_gym_detail_without_score(app_client: AsyncClient):
    # 既存ダミー slug を想定（なければ seed 側の slug に合わせて変更）
    r = await app_client.get("/gyms/dummy-funabashi-east")
    assert r.status_code == 200
    j = r.json()
    assert "score" not in j or j["score"] is None
    assert "freshness" not in j or j["freshness"] is None
    assert "richness" not in j or j["richness"] is None


async def test_gym_detail_with_score(app_client: AsyncClient):
    r = await app_client.get("/gyms/dummy-funabashi-east?include=score")
    assert r.status_code == 200
    j = r.json()
    assert 0.0 <= j["freshness"] <= 1.0
    assert 0.0 <= j["richness"] <= 1.0
    assert 0.0 <= j["score"] <= 1.0
