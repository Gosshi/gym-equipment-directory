"""Integration tests covering service readiness/health endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration]


def test_health_endpoint_reports_ok(integration_client: TestClient) -> None:
    """/health should respond with a JSON payload when the app boots."""
    response = integration_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    assert "env" in payload


def test_readyz_endpoint_checks_database(integration_client: TestClient) -> None:
    """/readyz performs a database round trip and should succeed."""
    response = integration_client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
