"""Integration tests covering service readiness/health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration]


async def test_health_endpoint_reports_ok(integration_client: AsyncClient) -> None:
    """/health should respond with a JSON payload when the app boots."""
    response = await integration_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    assert "env" in payload


async def test_readyz_endpoint_checks_database(integration_client: AsyncClient) -> None:
    """/readyz performs a database round trip and should succeed."""
    response = await integration_client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
