import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_report_success(app_client: AsyncClient):
    payload = {
        "type": "wrong_info",
        "message": "ジム情報が古いようです",
        "email": "user@example.com",
        "source_url": "https://example.com/proof",
    }
    r = await app_client.post("/gyms/dummy-funabashi-east/report", json=payload)
    assert r.status_code == 201
    j = r.json()
    assert isinstance(j.get("id"), int)
    assert j.get("status") == "open"


@pytest.mark.asyncio
async def test_post_report_validation_errors(app_client: AsyncClient):
    # too short message
    r1 = await app_client.post(
        "/gyms/dummy-funabashi-east/report",
        json={"type": "wrong_info", "message": "ng"},
    )
    assert r1.status_code == 422

    # invalid type
    r2 = await app_client.post(
        "/gyms/dummy-funabashi-east/report",
        json={"type": "invalid", "message": "valid message"},
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_admin_list_and_resolve(app_client: AsyncClient):
    # create two reports
    for msg in ("A valid message one", "A valid message two"):
        await app_client.post(
            "/gyms/dummy-funabashi-east/report",
            json={"type": "other", "message": msg},
        )

    r = await app_client.get("/admin/reports", params={"status": "open", "limit": 10})
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j.get("items"), list)
    assert len(j["items"]) >= 2
    first_id = j["items"][0]["id"]

    # resolve first
    r2 = await app_client.patch(f"/admin/reports/{first_id}:resolve")
    assert r2.status_code == 200
    assert r2.json().get("status") == "resolved"

    # open list should not include resolved item at the top after refetch
    r3 = await app_client.get("/admin/reports", params={"status": "open", "limit": 100})
    ids = [it["id"] for it in r3.json()["items"]]
    assert first_id not in ids
