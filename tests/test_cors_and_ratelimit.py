import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_cors_allowed_origin(monkeypatch):
    monkeypatch.setenv("ALLOW_ORIGINS", "http://localhost:3000,https://example.com")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health", headers={"Origin": "http://localhost:3000"})
        # When allowed, Starlette adds ACAO echoing the origin
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_default_allows_local(monkeypatch):
    monkeypatch.delenv("ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

        r_local_ip = await ac.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
        assert r_local_ip.status_code == 200
        assert r_local_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


@pytest.mark.asyncio
async def test_cors_default_prod_only_localhost(monkeypatch):
    monkeypatch.delenv("ALLOW_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

        r_local_ip = await ac.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
        assert r_local_ip.status_code == 200
        assert r_local_ip.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_cors_disallowed_origin(monkeypatch):
    monkeypatch.setenv("ALLOW_ORIGINS", "https://example.com")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health", headers={"Origin": "http://evil.com"})
        # Not allowed: middleware should not include ACAO header
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_rate_limit_get_exceeded(monkeypatch):
    # Ensure limiter is enabled during tests
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    # Keep CORS simple
    monkeypatch.setenv("ALLOW_ORIGINS", "")

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Hit limit for GET: 60/minute, 61st must be 429
        for _ in range(60):
            r = await ac.get("/health")
            assert r.status_code == 200
        r = await ac.get("/health")
        assert r.status_code == 429
        body = r.json()
        assert "error" in body
        assert body["error"].get("code") == "rate_limited"
