import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_healthz_ok_without_sentry(monkeypatch):
    # Ensure SENTRY_DSN is unset
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


@pytest.mark.asyncio
async def test_debug_error_disabled_in_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/debug/error")
        assert r.status_code == 404
