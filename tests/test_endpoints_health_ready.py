import pytest


@pytest.mark.anyio
async def test_healthz_ok(app_client):
    resp = await app_client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True}


@pytest.mark.anyio
async def test_readyz_ok(app_client):
    resp = await app_client.get("/readyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True}
