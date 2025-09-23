import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_search_per_page_boundary_one(app_client: AsyncClient):
    r = await app_client.get("/gyms/search", params={"page_size": 1})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and isinstance(body["items"], list)
    assert len(body["items"]) <= 1
    assert body.get("page_size") == 1
    assert "has_more" in body
    assert "has_prev" in body
