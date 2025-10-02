from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gym
from app.models.gym_slug import GymSlug


async def set_current_slug(session: AsyncSession, gym: Gym, new_slug: str) -> None:
    """Ensure the given slug is the current canonical slug for the gym."""

    if not new_slug:
        raise ValueError("new_slug must not be empty")
    if gym.id is None:
        raise ValueError("gym must be persisted before updating slugs")

    gym_id = int(gym.id)

    await session.execute(
        update(GymSlug)
        .where(GymSlug.gym_id == gym_id, GymSlug.slug != new_slug, GymSlug.is_current.is_(True))
        .values(is_current=False)
    )

    insert_stmt = (
        insert(GymSlug)
        .values(gym_id=gym_id, slug=new_slug, is_current=True)
        .on_conflict_do_nothing(index_elements=[GymSlug.slug])
    )
    await session.execute(insert_stmt)

    await session.execute(
        update(GymSlug)
        .where(GymSlug.gym_id == gym_id, GymSlug.slug == new_slug)
        .values(is_current=True)
    )

    if gym.slug != new_slug:
        gym.slug = new_slug
    await session.flush()
