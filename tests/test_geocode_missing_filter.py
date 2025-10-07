from __future__ import annotations

import uuid

import pytest

from app.models.gym import Gym
from scripts.tools import geocode_missing


@pytest.mark.asyncio
async def test_geocode_missing_excludes_manual_origin(session, monkeypatch):
    gym = Gym(
        name="Manual Gym",
        slug=f"manual-gym-{uuid.uuid4()}",
        canonical_id=str(uuid.uuid4()),
        address="東京都千代田区千代田1-1",
        official_url="manual:https://example.com",
    )
    session.add(gym)
    await session.flush()

    async def fail_geocode(*_args, **_kwargs):
        raise AssertionError("Manual gym should not be geocoded when origin is scraped")

    monkeypatch.setattr(geocode_missing, "geocode", fail_geocode)

    summary = await geocode_missing.geocode_missing_records(
        "gyms", origin="scraped", session=session
    )

    assert summary == {"tried": 0, "updated": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_geocode_missing_includes_manual_origin_when_all(session, monkeypatch):
    gym = Gym(
        name="Manual Gym",
        slug=f"manual-gym-{uuid.uuid4()}",
        canonical_id=str(uuid.uuid4()),
        address="東京都千代田区千代田1-1",
        official_url="manual:https://example.com",
    )
    session.add(gym)
    await session.flush()

    async def fake_geocode(_session, address: str):
        assert address
        return 35.1234, 139.9876

    monkeypatch.setattr(geocode_missing, "geocode", fake_geocode)

    summary = await geocode_missing.geocode_missing_records(
        "gyms", origin="all", session=session
    )

    await session.refresh(gym)

    assert summary == {"tried": 1, "updated": 1, "skipped": 0}
    assert gym.latitude == pytest.approx(35.1234)
    assert gym.longitude == pytest.approx(139.9876)
