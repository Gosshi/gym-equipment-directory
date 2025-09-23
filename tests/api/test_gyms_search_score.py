# tests/api/test_gyms_search_score.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_score_sort_paging(app_client: AsyncClient):
    r1 = await app_client.get("/gyms/search", params={"sort": "score", "page_size": 2})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1.get("page") == 1
    assert j1.get("page_size") == 2
    assert "items" in j1 and "has_more" in j1
    if j1["has_more"]:
        next_page = (j1.get("page") or 1) + 1
        r2 = await app_client.get(
            "/gyms/search", params={"sort": "score", "page_size": 2, "page": next_page}
        )
        assert r2.status_code == 200
        j2 = r2.json()
        # 二重取得していないこと（緩めの検査）
        ids1 = [it["id"] for it in j1["items"]]
        ids2 = [it["id"] for it in j2["items"]]
        assert set(ids1).isdisjoint(ids2)


@pytest.mark.asyncio
async def test_sorts_basic(app_client):
    for s in ["score", "freshness", "richness", "gym_name", "created_at"]:
        r = await app_client.get("/gyms/search", params={"sort": s, "page_size": 2})
        assert r.status_code == 200
        j = r.json()
        assert "items" in j
        assert j.get("page") == 1
        assert j.get("page_size") == 2
        assert "has_more" in j
        assert "has_prev" in j
        assert j["has_prev"] is False
