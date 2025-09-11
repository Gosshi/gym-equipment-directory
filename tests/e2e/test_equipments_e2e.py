import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_equipments_filter_and_limit(app_client: AsyncClient):
    # Basic list
    r1 = await app_client.get("/equipments")
    assert r1.status_code == 200
    all_items = r1.json()
    assert isinstance(all_items, list)
    assert len(all_items) >= 0

    # Filter by partial slug from seed data (see tests/conftest.py)
    r2 = await app_client.get("/equipments", params={"q": "seed-bench"})
    assert r2.status_code == 200
    items = r2.json()
    slugs = [it["slug"] for it in items]
    assert any(s.startswith("seed-bench") for s in slugs)

    # Limit boundary
    r3 = await app_client.get("/equipments", params={"limit": 1})
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)
    assert len(r3.json()) <= 1
