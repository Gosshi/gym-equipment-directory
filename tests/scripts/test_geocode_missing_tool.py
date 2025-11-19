from __future__ import annotations

import uuid

import pytest

from app.models.gym import Gym
from scripts.tools import geocode_missing


@pytest.mark.asyncio
async def test_geocode_missing_records_returns_summary(session, monkeypatch):
    gym = Gym(
        name="Ops Gym",
        slug=f"ops-gym-{uuid.uuid4()}",
        canonical_id=str(uuid.uuid4()),
        address="東京都千代田区千代田1-1",
    )
    session.add(gym)
    await session.flush()

    async def fake_geocode(_session, address: str):
        assert address
        return 35.6, 139.7

    monkeypatch.setattr(geocode_missing, "geocode", fake_geocode)

    summary = await geocode_missing.geocode_missing_records(
        "gyms",
        origin="all",
        dry_run=True,
        session=session,
    )

    assert summary["tried"] == 1
    assert summary["updated"] == 1
    assert summary["skipped"] == 0
    assert summary["reasons"] == {}
