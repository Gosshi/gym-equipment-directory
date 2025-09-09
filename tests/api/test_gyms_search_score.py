# tests/api/test_gyms_search_score.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_score_sort_paging(app_client: AsyncClient):
    r1 = await app_client.get("/gyms/search", params={"sort": "score", "per_page": 2})
    assert r1.status_code == 200
    j1 = r1.json()
    assert "items" in j1 and "has_next" in j1 and "page_token" in j1
    if j1["has_next"]:
        assert j1["page_token"] is not None
        r2 = await app_client.get(
            "/gyms/search", params={"sort": "score", "per_page": 2, "page_token": j1["page_token"]}
        )
        assert r2.status_code == 200
        j2 = r2.json()
        # 二重取得していないこと（緩めの検査）
        ids1 = [it["id"] for it in j1["items"]]
        ids2 = [it["id"] for it in j2["items"]]
        assert set(ids1).isdisjoint(ids2)
    else:
        assert j1["page_token"] is None


@pytest.mark.asyncio
async def test_sorts_basic(app_client):
    for s in ["score", "freshness", "richness", "gym_name", "created_at"]:
        r = await app_client.get("/gyms/search", params={"sort": s, "per_page": 2})
        assert r.status_code == 200
        j = r.json()
        assert "items" in j and "has_next" in j and "page_token" in j
        if not j["has_next"]:
            assert j["page_token"] is None
