from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.models.equipment import Equipment
from app.models.gym import Gym
from app.models.gym_equipment import GymEquipment
from scripts import update_freshness as update_freshness_script


@pytest.mark.asyncio
async def test_update_freshness_returns_summary(session):
    slug = f"freshness-gym-{uuid.uuid4()}"
    gym = Gym(
        name="Freshness Gym",
        slug=slug,
        canonical_id=slug,
        address="千葉県船橋市…",
        last_verified_at_cached=None,
    )
    equipment_slug = f"ops-bench-{uuid.uuid4()}"
    equipment = Equipment(slug=equipment_slug, name="Ops Bench", category="free_weight")
    session.add_all([gym, equipment])
    await session.flush()

    verification_time = datetime.utcnow() - timedelta(days=1)
    session.add(
        GymEquipment(
            gym_id=gym.id,
            equipment_id=equipment.id,
            last_verified_at=verification_time,
        )
    )
    await session.flush()

    summary = await update_freshness_script.update_freshness(async_engine=session.bind)

    await session.refresh(gym)

    assert summary["reset_rows"] >= 1
    assert summary["updated_rows"] >= 1
    assert gym.last_verified_at_cached == verification_time
