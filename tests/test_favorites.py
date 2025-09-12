import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_favorites_crud_idempotent(app_client: AsyncClient):
    device_id = "dev-abc-123"
    gym_id = 1  # seeded gym

    # POST create (idempotent)
    r1 = await app_client.post(
        "/me/favorites",
        json={"device_id": device_id, "gym_id": gym_id},
    )
    assert r1.status_code == 204

    # POST again -> still 204
    r2 = await app_client.post(
        "/me/favorites",
        json={"device_id": device_id, "gym_id": gym_id},
    )
    assert r2.status_code == 204

    # GET list
    r3 = await app_client.get("/me/favorites", params={"device_id": device_id})
    assert r3.status_code == 200
    items = r3.json()
    assert isinstance(items, list)
    assert any(it["gym_id"] == gym_id for it in items)
    # fields shape
    item = next(it for it in items if it["gym_id"] == gym_id)
    for k in ("slug", "name", "pref", "city", "last_verified_at"):
        assert k in item

    # DELETE (idempotent)
    r4 = await app_client.delete(f"/me/favorites/{gym_id}", params={"device_id": device_id})
    assert r4.status_code == 204

    # DELETE again -> still 204
    r5 = await app_client.delete(f"/me/favorites/{gym_id}", params={"device_id": device_id})
    assert r5.status_code == 204

    # list should be empty (or not contain gym)
    r6 = await app_client.get("/me/favorites", params={"device_id": device_id})
    assert r6.status_code == 200
    items2 = r6.json()
    assert all(it["gym_id"] != gym_id for it in items2)


@pytest.mark.asyncio
async def test_favorites_device_id_validation(app_client: AsyncClient):
    bad_ids = ["short", "bad$symbol", "white space", "あいうえお"]
    for bad in bad_ids:
        # POST invalid
        r1 = await app_client.post(
            "/me/favorites",
            json={"device_id": bad, "gym_id": 1},
        )
        assert r1.status_code == 422

        # GET invalid
        r2 = await app_client.get("/me/favorites", params={"device_id": bad})
        assert r2.status_code == 422

        # DELETE invalid
        r3 = await app_client.delete("/me/favorites/1", params={"device_id": bad})
        assert r3.status_code == 422
