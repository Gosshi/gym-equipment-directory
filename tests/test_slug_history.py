from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gym
from app.models.gym_slug import GymSlug


@pytest.mark.asyncio
async def test_gym_detail_resolves_old_slug(app_client: AsyncClient, session: AsyncSession) -> None:
    gym = Gym(
        name="履歴ジム",
        slug="new-slug",
        canonical_id=str(uuid4()),
        pref="tokyo",
        city="chiyoda",
    )
    session.add(gym)
    await session.flush()

    session.add(GymSlug(gym_id=int(gym.id), slug="new-slug", is_current=True))
    session.add(GymSlug(gym_id=int(gym.id), slug="old-slug", is_current=False))
    await session.commit()

    legacy_response = await app_client.get("/gyms/old-slug")
    assert legacy_response.status_code == 200
    legacy_payload = legacy_response.json()
    assert legacy_payload["canonical_slug"] == "new-slug"
    assert legacy_payload["requested_slug"] == "old-slug"
    assert legacy_payload["gym"]["slug"] == "new-slug"
    assert legacy_payload.get("meta", {}).get("redirect") is True

    canonical_response = await app_client.get("/gyms/new-slug")
    assert canonical_response.status_code == 200
    canonical_payload = canonical_response.json()
    assert canonical_payload["canonical_slug"] == "new-slug"
    assert canonical_payload["requested_slug"] == "new-slug"
    assert canonical_payload["gym"]["id"] == legacy_payload["gym"]["id"]
    assert canonical_payload["equipments"] == legacy_payload["equipments"]
