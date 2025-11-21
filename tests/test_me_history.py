from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_history_get_returns_empty_items(app_client: AsyncClient):
    response = await app_client.get("/me/history")

    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"gymId": 1},
        {"gymIds": [1, 2, 3]},
    ],
)
async def test_history_post_accepts_single_or_multiple_ids(app_client: AsyncClient, payload: dict):
    response = await app_client.post("/me/history", json=payload)

    assert response.status_code == 204


async def test_history_post_requires_payload(app_client: AsyncClient):
    response = await app_client.post("/me/history", json={})

    assert response.status_code == 422
