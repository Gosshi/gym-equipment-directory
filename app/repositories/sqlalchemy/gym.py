"""SQLAlchemy implementation of gym repository interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models import Equipment, Gym, GymEquipment, GymSlug, Source
from app.models.gym_image import GymImage
from app.repositories.interfaces import (
    GymEquipmentBasicRow,
    GymEquipmentSummaryRow,
    GymImageRow,
    GymReadRepository,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _enum_to_str(value) -> str | None:  # type: ignore[no-untyped-def]
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


class SqlAlchemyGymReadRepository(GymReadRepository):
    """Default SQLAlchemy-backed implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_pref_city(self, *, pref: str | None, city: str | None) -> list[Gym]:
        stmt = select(Gym)
        if pref:
            stmt = stmt.where(func.lower(Gym.pref) == func.lower(pref))
        if city:
            stmt = stmt.where(func.lower(Gym.city) == func.lower(city))
        return (await self._session.scalars(stmt)).all()

    async def created_at_map(self, gym_ids: Sequence[int]) -> dict[int, datetime | None]:
        if not gym_ids:
            return {}
        stmt = select(Gym.id, Gym.created_at).where(Gym.id.in_(gym_ids))
        rows = await self._session.execute(stmt)
        return {int(row.id): row.created_at for row in rows.all()}

    async def fetch_equipment_basic(self, gym_id: int) -> list[GymEquipmentBasicRow]:
        stmt = (
            select(
                Equipment.slug.label("equipment_slug"),
                Equipment.name.label("equipment_name"),
                Equipment.category,
                GymEquipment.count,
                GymEquipment.max_weight_kg,
            )
            .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
            .where(GymEquipment.gym_id == gym_id)
            .order_by(Equipment.name)
        )
        rows = await self._session.execute(stmt)
        return [
            GymEquipmentBasicRow(
                gym_id=gym_id,
                equipment_slug=row.equipment_slug,
                equipment_name=row.equipment_name,
                category=row.category,
                count=row.count,
                max_weight_kg=row.max_weight_kg,
            )
            for row in rows.all()
        ]

    async def fetch_equipment_summaries(self, gym_id: int) -> list[GymEquipmentSummaryRow]:
        stmt = (
            select(
                Equipment.slug,
                Equipment.name,
                Equipment.category,
                GymEquipment.count,
                GymEquipment.max_weight_kg,
                GymEquipment.availability,
                GymEquipment.verification_status,
                GymEquipment.last_verified_at,
                Source.url,
            )
            .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
            .join(Source, Source.id == GymEquipment.source_id, isouter=True)
            .where(GymEquipment.gym_id == gym_id)
            .order_by(Equipment.name)
        )
        rows = await self._session.execute(stmt)
        return [
            GymEquipmentSummaryRow(
                gym_id=gym_id,
                slug=row.slug,
                name=row.name,
                category=row.category,
                count=row.count,
                max_weight_kg=row.max_weight_kg,
                availability=_enum_to_str(row.availability),
                verification_status=_enum_to_str(row.verification_status),
                last_verified_at=row.last_verified_at,
                source=row.url,
            )
            for row in rows.all()
        ]

    async def fetch_equipment_for_gyms(
        self,
        *,
        gym_ids: Sequence[int],
        equipment_slugs: Sequence[str] | None,
    ) -> list[GymEquipmentSummaryRow]:
        if not gym_ids:
            return []

        stmt = (
            select(
                GymEquipment.gym_id,
                Equipment.slug,
                Equipment.name,
                Equipment.category,
                GymEquipment.availability,
                GymEquipment.verification_status,
                GymEquipment.last_verified_at,
                GymEquipment.count,
                GymEquipment.max_weight_kg,
                Source.url,
            )
            .join(Equipment, Equipment.id == GymEquipment.equipment_id)
            .join(Source, Source.id == GymEquipment.source_id, isouter=True)
            .where(GymEquipment.gym_id.in_(gym_ids))
        )
        if equipment_slugs:
            stmt = stmt.where(Equipment.slug.in_(equipment_slugs))

        rows = await self._session.execute(stmt)
        return [
            GymEquipmentSummaryRow(
                gym_id=row.gym_id,
                slug=row.slug,
                name=row.name,
                category=row.category,
                count=row.count,
                max_weight_kg=row.max_weight_kg,
                availability=_enum_to_str(row.availability),
                verification_status=_enum_to_str(row.verification_status),
                last_verified_at=row.last_verified_at,
                source=row.url,
            )
            for row in rows.all()
        ]

    async def fetch_images(self, gym_id: int) -> list[GymImageRow]:
        stmt = (
            select(
                GymImage.url,
                GymImage.source,
                GymImage.verified,
                GymImage.created_at,
            )
            .where(GymImage.gym_id == gym_id)
            .order_by(GymImage.created_at.desc(), GymImage.id.desc())
        )
        rows = await self._session.execute(stmt)
        return [
            GymImageRow(
                gym_id=gym_id,
                url=row.url,
                source=row.source,
                verified=bool(row.verified),
                created_at=row.created_at,
            )
            for row in rows.all()
        ]

    async def get_by_slug(self, slug: str) -> Gym | None:
        return await self._session.scalar(select(Gym).where(Gym.slug == slug))

    async def get_by_slug_from_history(self, slug: str) -> Gym | None:
        stmt = select(Gym).join(GymSlug, GymSlug.gym_id == Gym.id).where(GymSlug.slug == slug)
        return await self._session.scalar(stmt)

    async def get_by_canonical_id(self, canonical_id: str) -> Gym | None:
        return await self._session.scalar(select(Gym).where(Gym.canonical_id == canonical_id))

    async def get_by_id(self, gym_id: int) -> Gym | None:
        return await self._session.get(Gym, gym_id)

    async def resolve_id_by_slug(self, slug: str) -> int | None:
        gym_id = await self._session.scalar(select(Gym.id).where(Gym.slug == slug))
        if gym_id is None:
            gym_id = await self._session.scalar(select(GymSlug.gym_id).where(GymSlug.slug == slug))
        return int(gym_id) if gym_id is not None else None

    async def count_gym_equipments(self, gym_id: int) -> int:
        stmt = select(func.count()).select_from(GymEquipment).where(GymEquipment.gym_id == gym_id)
        count = await self._session.scalar(stmt)
        return int(count or 0)

    async def max_gym_equipments(self) -> int:
        subq = (
            select(GymEquipment.gym_id.label("gid"), func.count().label("c"))
            .group_by(GymEquipment.gym_id)
            .subquery()
        )
        stmt = select(func.coalesce(func.max(subq.c.c), 0))
        max_count = await self._session.scalar(stmt)
        return int(max_count or 0)
