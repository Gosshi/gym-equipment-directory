"""Integration smoke tests that hit representative public endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from scripts.seed_min_test import MINIMAL_GYM_DATASET

pytestmark = [pytest.mark.integration]

_NEARBY_PARAMS = {"lat": 35.6595, "lng": 139.7005, "radius_km": 5.0}


async def test_gym_nearby_endpoint_returns_seed_data(integration_client: AsyncClient) -> None:
    """/gyms/nearby should return the seeded dataset with full pagination metadata."""
    response = await integration_client.get(
        "/gyms/nearby",
        params={**_NEARBY_PARAMS, "page_size": 5},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == len(MINIMAL_GYM_DATASET)
    assert payload["page"] == 1
    assert payload["page_size"] == 5
    assert payload["has_more"] is False
    assert payload["has_prev"] is False
    assert payload["page_token"] is None

    items = payload.get("items", [])
    assert len(items) == len(MINIMAL_GYM_DATASET)

    first = items[0]
    assert first["slug"] == "integration-hub-gym"
    assert first["distance_km"] == pytest.approx(0.0, abs=1e-6)
    expected_keys = {
        "id",
        "slug",
        "name",
        "pref",
        "city",
        "latitude",
        "longitude",
        "distance_km",
        "last_verified_at",
    }
    assert expected_keys.issubset(first.keys())


async def test_gym_nearby_endpoint_supports_offset_pagination(
    integration_client: AsyncClient,
) -> None:
    """Offset pagination (page/page_size) should surface the second seeded gym on page 2."""
    response = await integration_client.get(
        "/gyms/nearby",
        params={**_NEARBY_PARAMS, "page": 2, "page_size": 1},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == len(MINIMAL_GYM_DATASET)
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert payload["has_more"] is True
    assert payload["has_prev"] is True
    assert payload["page_token"] is None

    items = payload.get("items", [])
    assert len(items) == 1
    second = items[0]
    assert second["slug"] == "integration-riverside-gym"
    assert second["distance_km"] == pytest.approx(0.214907, rel=1e-3)
    assert {"id", "slug", "name"}.issubset(second.keys())
