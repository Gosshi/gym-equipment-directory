from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Equipment, Gym, GymEquipment, Source
from app.models.gym_equipment import Availability, VerificationStatus


@pytest.mark.anyio
async def test_gym_detail_includes_gym_equipments(app_client, session):
    # Arrange: attach a Source and set fields on one GymEquipment
    gym = await session.scalar(select(Gym).where(Gym.slug == "dummy-funabashi-east"))
    assert gym is not None

    ge = await session.scalar(select(GymEquipment).where(GymEquipment.gym_id == gym.id))
    assert ge is not None

    # find equipment to get slug for later check
    eq = await session.scalar(select(Equipment).where(Equipment.id == ge.equipment_id))
    assert eq is not None

    src = Source(url="https://example.com/src", title="seed", source_type="other")
    session.add(src)
    await session.flush()

    ge.availability = Availability.present
    ge.verification_status = VerificationStatus.user_verified
    ge.last_verified_at = datetime.now(UTC) - timedelta(days=1)
    ge.source_id = src.id
    await session.commit()

    # Act
    resp = await app_client.get(f"/gyms/{gym.slug}")
    assert resp.status_code == 200
    body = resp.json()

    # Assert
    assert "gym_equipments" in body
    items = body["gym_equipments"]
    assert isinstance(items, list) and len(items) >= 1

    # find our updated one
    target = next((it for it in items if it["slug"] == eq.slug), None)
    assert target is not None
    for k in [
        "slug",
        "name",
        "availability",
        "verification_status",
        "last_verified_at",
        "source",
    ]:
        assert k in target

    assert target["availability"] == "present"
    assert target["verification_status"] == "user_verified"
    assert target["source"] == src.url
