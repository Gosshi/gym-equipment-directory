"""Backend smoke tests that avoid touching the database."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.smoke
def test_healthz_endpoint_is_up(client: TestClient) -> None:
    """/healthz should be reachable without hitting the database."""
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True


@pytest.mark.smoke
def test_openapi_schema_is_available(client: TestClient) -> None:
    """The OpenAPI schema should be served for lightweight validation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/healthz" in schema["paths"]
