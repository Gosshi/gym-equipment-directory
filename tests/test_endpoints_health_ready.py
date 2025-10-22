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


@pytest.mark.anyio
async def test_readyz_returns_503_before_migrations(app_client, monkeypatch):
    monkeypatch.setattr("app.api.routers.readyz.is_migration_completed", lambda: False)

    resp = await app_client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json() == {
        "error": {
            "code": "migrations_pending",
            "message": "Database migrations are still running",
        }
    }
