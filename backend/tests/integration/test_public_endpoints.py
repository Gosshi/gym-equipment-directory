"""Integration smoke tests that hit representative public endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration]


def test_gym_search_endpoint_returns_json(integration_client: TestClient) -> None:
    """/gyms/search should respond with pagination metadata even on an empty database."""
    response = integration_client.get("/gyms/search")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("items"), list)
    assert "total" in payload
    assert "page" in payload
    assert "page_size" in payload
    assert "has_more" in payload
    assert "has_prev" in payload
    # page_token may be null but must exist in the payload.
    assert "page_token" in payload
