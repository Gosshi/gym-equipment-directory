from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_request_id_echoes_back(app_client):
    rid = "test-123"
    res = await app_client.get("/healthz", headers={"X-Request-ID": rid})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == rid


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(app_client):
    res = await app_client.get("/healthz")
    assert res.status_code == 200
    rid = res.headers.get("X-Request-ID")
    assert isinstance(rid, str)
    assert len(rid) > 0  # UUID-like, non-empty


@pytest.mark.asyncio
async def test_gyms_search_returns_200(app_client):
    res = await app_client.get("/gyms/search")
    assert res.status_code == 200
