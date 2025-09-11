import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_gym_detail_not_found_returns_404(app_client: AsyncClient):
    r = await app_client.get("/gyms/this-slug-does-not-exist")
    assert r.status_code == 404
    j = r.json()
    # FastAPI default error schema has a 'detail' key
    assert j.get("detail") in ("gym not found", "Not Found")
