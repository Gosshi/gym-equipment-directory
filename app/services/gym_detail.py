from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymEquipment
from app.repositories.gym_repository import GymRepository
from app.schemas.gym_detail import GymDetailResponse
from app.services.scoring import compute_bundle


async def _count_equips(session: AsyncSession, gym_id: int) -> int:
    stmt = select(func.count()).select_from(GymEquipment).where(GymEquipment.gym_id == gym_id)
    return (await session.execute(stmt)).scalar_one()


async def _max_gym_equips(session: AsyncSession) -> int:
    sub = (
        select(GymEquipment.gym_id, func.count().label("c"))
        .group_by(GymEquipment.gym_id)
        .subquery()
    )
    stmt = select(func.coalesce(func.max(sub.c.c), 0))
    return (await session.execute(stmt)).scalar_one()


def _iso(dt: datetime | None) -> str | None:
    if not dt or (hasattr(dt, "year") and dt.year < 1970):
        return None
    return dt.isoformat()


async def get_gym_detail(
    session: AsyncSession, slug: str, include: str | None
) -> GymDetailResponse:
    # Resolve the gym id by slug first (index on slug exists)
    gym_id = await session.scalar(select(Gym.id).where(Gym.slug == slug))
    if not gym_id:
        raise HTTPException(status_code=404, detail="gym not found")

    # Use repository to load the entity by id
    repo = GymRepository(session)
    gym = await repo.get_by_id(int(gym_id))
    if not gym:
        # Defensive: id not found after slug resolution (should not happen)
        raise HTTPException(status_code=404, detail="gym not found")

    # Equipments list
    eq_rows = await session.execute(
        select(
            Equipment.slug,
            Equipment.name,
            Equipment.category,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
        )
        .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.name)
    )
    equipments_list = [
        {
            "equipment_slug": slug,
            "equipment_name": name,
            "category": category,
            "count": count,
            "max_weight_kg": max_w,
        }
        for (slug, name, category, count, max_w) in eq_rows.all()
    ]

    data = {
        "id": int(getattr(gym, "id", 0)),
        "slug": str(getattr(gym, "slug", "")),
        "name": str(getattr(gym, "name", "")),
        "pref": getattr(gym, "pref", None),
        "city": str(getattr(gym, "city", "")),
        "updated_at": _iso(getattr(gym, "updated_at", None)),
        "last_verified_at": _iso(getattr(gym, "last_verified_at_cached", None)),
        "equipments": equipments_list,
    }

    if include == "score":
        num = await _count_equips(session, int(getattr(gym, "id", 0)))
        mx = await _max_gym_equips(session)
        bundle = compute_bundle(getattr(gym, "last_verified_at_cached", None), num, mx)
        data["freshness"] = bundle.freshness
        data["richness"] = bundle.richness
        data["score"] = bundle.score

    return GymDetailResponse.model_validate(data)
