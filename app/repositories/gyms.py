from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymEquipment


async def list_candidate_gyms(
    db: AsyncSession, pref: str | None = None, city: str | None = None
) -> list[Gym]:
    """Return candidate Gym rows filtered by optional pref/city (preserves DB ordering by id)."""
    q = select(Gym)
    if pref:
        q = q.where(func.lower(Gym.pref) == func.lower(pref))
    if city:
        q = q.where(func.lower(Gym.city) == func.lower(city))
    rows = (await db.scalars(q.order_by(Gym.id))).all()
    return list(rows)


async def get_gym_by_slug(db: AsyncSession, slug: str) -> Gym | None:
    """Fetch a single Gym by slug or return None."""
    return await db.scalar(select(Gym).where(Gym.slug == slug))


async def list_gym_equipments(
    db: AsyncSession, gym_ids: Sequence[int], equipment_slugs: Iterable[str] | None = None
) -> list[Any]:
    """Return rows for equipments joined with gym_equipment for given gym_ids.

    Each row is the SQLAlchemy Row mapping with attributes used by callers.
    """
    q = (
        select(
            GymEquipment.gym_id,
            Equipment.slug.label("equipment_slug"),
            Equipment.name.label("equipment_name"),
            Equipment.category,
            GymEquipment.availability,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
            GymEquipment.verification_status,
            GymEquipment.last_verified_at,
        )
        .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        .where(GymEquipment.gym_id.in_(list(gym_ids)))
    )
    if equipment_slugs:
        q = q.where(Equipment.slug.in_(list(equipment_slugs)))
    res = (await db.execute(q)).all()
    return list(res)


async def count_equips_grouped(db: AsyncSession) -> int:
    """Return the maximum number of equipments any gym has (coalesced to 0)."""
    subq = (
        select(GymEquipment.gym_id, func.count().label("cnt"))
        .group_by(GymEquipment.gym_id)
        .subquery()
    )
    val = await db.scalar(select(func.coalesce(func.max(subq.c.cnt), 0)))
    return int(val or 0)
