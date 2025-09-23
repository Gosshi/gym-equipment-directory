import pytest


@pytest.mark.asyncio
async def test_get_gym_detail_success(app_client):
    resp = await app_client.get("/gyms/funabashi-station-gym")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "funabashi-station-gym"
    assert data["name"].startswith("テストジム")
    assert any(eq["equipment_slug"] == "squat-rack" for eq in data["equipments"])
    detail_map = {entry["slug"]: entry for entry in data["gym_equipments"]}
    assert "squat-rack" in detail_map
    assert detail_map["squat-rack"]["availability"] == "present"


@pytest.mark.asyncio
async def test_get_gym_detail_with_score(app_client):
    resp = await app_client.get("/gyms/funabashi-station-gym", params={"include": "score"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] is not None
    assert data["freshness"] is not None
    assert data["richness"] is not None


@pytest.mark.asyncio
async def test_get_gym_detail_not_found(app_client):
    resp = await app_client.get("/gyms/unknown-gym")
    assert resp.status_code == 404
