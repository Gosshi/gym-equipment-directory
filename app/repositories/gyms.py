from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymEquipment


async def get_by_slug(session: AsyncSession, slug: str) -> Gym | None:
    """Return Gym model by slug or None."""
    stmt = select(Gym).where(Gym.slug == slug)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_equipments_for_gym(
    session: AsyncSession, gym_id: int
) -> list[tuple[str, str, str | None, int | None, int | None]]:
    """Return list of tuples: (equipment_slug, equipment_name, category, count, max_weight_kg)."""
    stmt = (
        select(
            Equipment.slug,
            Equipment.name,
            Equipment.category,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
        )
        .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
        .where(GymEquipment.gym_id == gym_id)
        .order_by(Equipment.name)
    )
    rows = await session.execute(stmt)
    # rows.all() returns a Sequence[Row[...]]; convert to list of plain tuples
    return [tuple(r) for r in rows.all()]


async def count_gym_equips(session: AsyncSession, gym_id: int) -> int:
    stmt = select(func.count()).select_from(GymEquipment).where(GymEquipment.gym_id == gym_id)
    return (await session.execute(stmt)).scalar_one()


async def max_gym_equips(session: AsyncSession) -> int:
    sub = (
        select(GymEquipment.gym_id, func.count().label("c"))
        .group_by(GymEquipment.gym_id)
        .subquery()
    )
    stmt = select(func.coalesce(func.max(sub.c.c), 0))
    return (await session.execute(stmt)).scalar_one()
