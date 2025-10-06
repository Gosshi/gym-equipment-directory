from __future__ import annotations

import uuid

import pytest

from app.models.gym import Gym
from app.services import geocode as geocode_service
from scripts.tools import geocode_missing


@pytest.mark.asyncio
async def test_geocode_uses_cache(session, monkeypatch):
    calls = 0

    def fake_nominatim(address: str):
        nonlocal calls
        calls += 1
        return 35.0, 139.0, {"lat": "35.0", "lon": "139.0"}

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(geocode_service, "nominatim_geocode", fake_nominatim)
    monkeypatch.setattr(geocode_service.asyncio, "to_thread", fake_to_thread)

    address = "東京都千代田区千代田1-1"

    result1 = await geocode_service.geocode(session, address)
    assert result1 == (35.0, 139.0)
    assert calls == 1

    result2 = await geocode_service.geocode(session, address)
    assert result2 == (35.0, 139.0)
    assert calls == 1


@pytest.mark.asyncio
async def test_geocode_missing_updates_records(session, monkeypatch):
    gym = Gym(
        name="Geocode Test Gym",
        slug="geocode-test-gym",
        canonical_id=str(uuid.uuid4()),
        address="東京都千代田区千代田1-1",
    )
    session.add(gym)
    await session.flush()

    async def fake_geocode(_, address: str):
        assert address
        return 34.1234, 135.5678

    monkeypatch.setattr(geocode_missing, "geocode", fake_geocode)

    summary = await geocode_missing.geocode_missing_records("gyms", limit=10, session=session)

    await session.refresh(gym)

    assert summary == {"tried": 1, "updated": 1, "skipped": 0}
    assert gym.latitude == pytest.approx(34.1234)
    assert gym.longitude == pytest.approx(135.5678)
