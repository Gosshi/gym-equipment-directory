import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gym


@pytest.mark.asyncio
async def test_get_gym_by_id_success(app_client: AsyncClient, session: AsyncSession) -> None:
    gym = await session.scalar(select(Gym).order_by(Gym.id))
    assert gym is not None

    resp = await app_client.get(f"/gyms/by-id/{gym.canonical_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["canonical_id"] == gym.canonical_id
    assert payload["slug"] == gym.slug


@pytest.mark.asyncio
async def test_get_gym_by_id_not_found(app_client: AsyncClient) -> None:
    resp = await app_client.get("/gyms/by-id/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_gym_by_id_invalid_uuid(app_client: AsyncClient) -> None:
    resp = await app_client.get("/gyms/by-id/not-a-uuid")
    assert resp.status_code == 404
