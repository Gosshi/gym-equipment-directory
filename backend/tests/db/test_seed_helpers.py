from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Equipment, GymEquipment
from app.models.gym_equipment import Availability, VerificationStatus
from scripts import seed as seed_script


@pytest.mark.asyncio
async def test_get_or_create_equipment_idempotent(db_session, faker):
    slug = faker.unique.slug()
    name = faker.word()
    eq1 = await seed_script.get_or_create_equipment(db_session, slug, name, "free_weight")
    eq2 = await seed_script.get_or_create_equipment(db_session, slug, name, "free_weight")
    assert eq1.id == eq2.id


@pytest.mark.asyncio
async def test_get_or_create_gym_overwrite_geo(db_session, faker):
    slug = faker.unique.slug()
    base = await seed_script.get_or_create_gym(
        db_session,
        slug=slug,
        name=faker.company(),
        pref="test-pref",
        city="test-city",
        address="Somewhere",
        latitude=None,
        longitude=None,
    )
    updated = await seed_script.get_or_create_gym(
        db_session,
        slug=slug,
        name=base.name,
        pref=base.pref,
        city=base.city,
        address=base.address,
        latitude=12.3456,
        longitude=78.9012,
        overwrite_geo=True,
    )
    assert updated.id == base.id
    assert updated.latitude == pytest.approx(12.3456)
    assert updated.longitude == pytest.approx(78.9012)


@pytest.mark.asyncio
async def test_link_gym_equipment_verification_status(db_session, faker):
    gym = await seed_script.get_or_create_gym(
        db_session,
        slug=faker.unique.slug(),
        name=faker.company(),
        pref="pref",
        city="city",
        address="addr",
        latitude=10.0,
        longitude=20.0,
    )
    eq_present = await seed_script.get_or_create_equipment(
        db_session, faker.unique.slug(), faker.word(), "other"
    )
    present = await seed_script.link_gym_equipment(
        db_session,
        gym,
        eq_present,
        availability=Availability.present,
        count=2,
        max_weight_kg=40,
        verification_status=VerificationStatus.unverified,
        last_verified_at=datetime.utcnow(),
    )
    assert present.verification_status == VerificationStatus.user_verified

    eq_absent = await seed_script.get_or_create_equipment(
        db_session, faker.unique.slug(), faker.word(), "other"
    )
    absent = await seed_script.link_gym_equipment(
        db_session,
        gym,
        eq_absent,
        availability=Availability.absent,
        verification_status=VerificationStatus.user_verified,
        last_verified_at=datetime.utcnow(),
    )
    assert absent.verification_status == VerificationStatus.unverified


@pytest.mark.asyncio
async def test_equipment_unique_constraint(db_session):
    equipment = Equipment(slug="unique-eq", name="Unique Eq", category="other")
    db_session.add(equipment)
    await db_session.flush()
    db_session.add(Equipment(slug="unique-eq", name="Dup", category="other"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_gym_equipment_foreign_key_violation(db_session):
    db_session.add(
        GymEquipment(
            gym_id=999999,
            equipment_id=999999,
            availability=Availability.unknown,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
