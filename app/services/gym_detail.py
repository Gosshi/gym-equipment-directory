from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import gyms as gyms_repo
from app.services import score as score_svc


async def get_detail(
    session: AsyncSession, slug: str, include_score: bool
) -> dict[str, Any] | None:
    """Build gym detail dict for pydantic validation.

    Returned dict matches GymDetailResponse schema expected by API.
    """
    gym = await gyms_repo.get_by_slug(session, slug)
    if not gym:
        return None  # router will handle 404 when it sees None

    eq_rows = await gyms_repo.list_equipments_for_gym(session, int(gym.id))
    equipments = [
        {
            "equipment_slug": slug,
            "equipment_name": name,
            "category": category,
            "count": count,
            "max_weight_kg": max_w,
        }
        for (slug, name, category, count, max_w) in eq_rows
    ]

    data = {
        "id": gym.id,
        "slug": gym.slug,
        "name": gym.name,
        "pref": getattr(gym, "pref", None),
        "city": gym.city,
        "updated_at": gym.updated_at.isoformat() if getattr(gym, "updated_at", None) else None,
        "last_verified_at": gym.last_verified_at_cached.isoformat()
        if getattr(gym, "last_verified_at_cached", None)
        else None,
        "equipments": equipments,
    }

    if include_score:
        num = await gyms_repo.count_gym_equips(session, int(gym.id))
        mx = await gyms_repo.max_gym_equips(session)
        bundle = score_svc.compute_bundle(gym.last_verified_at_cached, num, mx)
        data.update(bundle)

    return data
