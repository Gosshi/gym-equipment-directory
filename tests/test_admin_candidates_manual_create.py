from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymCandidate


async def _ensure_equipment(session: AsyncSession, slug: str) -> None:
    exists = await session.execute(select(Equipment).where(Equipment.slug == slug))
    if exists.scalar_one_or_none() is None:
        session.add(Equipment(slug=slug, name=slug.replace("-", " "), category="machine"))
        await session.commit()


@pytest.mark.asyncio
async def test_manual_candidate_create_and_approve(
    app_client: AsyncClient, session: AsyncSession
) -> None:
    await _ensure_equipment(session, "smith-machine")

    official_url = "https://example.com/manual-gym"
    payload = {
        "name_raw": "手動ジム",
        "address_raw": "東京都江東区",
        "pref_slug": "tokyo",
        "city_slug": "koto",
        "latitude": 35.6,
        "longitude": 139.8,
        "official_url": official_url,
        "equipments": [{"slug": "smith-machine", "availability": "present"}],
    }

    resp = await app_client.post("/admin/candidates", json=payload)
    assert resp.status_code in {200, 201}
    created = resp.json()
    assert created["name_raw"] == payload["name_raw"]
    assert created["pref_slug"] == payload["pref_slug"]
    assert created["city_slug"] == payload["city_slug"]

    candidate = await session.get(GymCandidate, created["id"])
    assert candidate is not None
    assert candidate.parsed_json is not None
    assert candidate.parsed_json.get("official_url") == official_url

    approve = await app_client.post(
        f"/admin/candidates/{created['id']}/approve", json={"dry_run": False}
    )
    assert approve.status_code == 200

    gym_result = await session.execute(select(Gym).where(Gym.official_url == official_url))
    gym = gym_result.scalar_one_or_none()
    assert gym is not None
