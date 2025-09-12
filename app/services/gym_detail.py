from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas as legacy_schemas
from app.models import Equipment, Gym, GymEquipment, Source
from app.models.gym_image import GymImage
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

    # gym_equipments: equipment + gym_equipment + source（左外部結合）を一括取得
    ge_rows = await session.execute(
        select(
            Equipment.slug,
            Equipment.name,
            GymEquipment.availability,
            GymEquipment.verification_status,
            GymEquipment.last_verified_at,
            Source.url,
        )
        .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
        .join(Source, Source.id == GymEquipment.source_id, isouter=True)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.name)
    )
    gym_equipments_list = []
    for (
        slug,
        name,
        availability,
        verification_status,
        last_verified_at,
        source_url,
    ) in ge_rows.all():
        avail = availability.value if hasattr(availability, "value") else str(availability)
        vstat = (
            verification_status.value
            if hasattr(verification_status, "value")
            else str(verification_status)
        )
        gym_equipments_list.append(
            {
                "slug": slug,
                "name": name,
                "availability": str(avail),
                "verification_status": str(vstat),
                "last_verified_at": last_verified_at,
                "source": source_url,
            }
        )

    data = {
        "id": int(getattr(gym, "id", 0)),
        "slug": str(getattr(gym, "slug", "")),
        "name": str(getattr(gym, "name", "")),
        "pref": getattr(gym, "pref", None),
        "city": str(getattr(gym, "city", "")),
        "updated_at": _iso(getattr(gym, "updated_at", None)),
        "last_verified_at": _iso(getattr(gym, "last_verified_at_cached", None)),
        "equipments": equipments_list,
        "gym_equipments": gym_equipments_list,
    }

    # images: gym_images rows for reference (no upload)
    img_rows = await session.execute(
        select(GymImage.url, GymImage.source, GymImage.verified, GymImage.created_at)
        .where(GymImage.gym_id == gym.id)
        .order_by(GymImage.created_at.desc(), GymImage.id.desc())
    )
    images_list = []
    for url, source, verified, created_at in img_rows.all():
        images_list.append(
            {
                "url": url,
                "source": source,
                "verified": bool(verified),
                "created_at": created_at,
            }
        )
    data["images"] = images_list

    if include == "score":
        num = await _count_equips(session, int(getattr(gym, "id", 0)))
        mx = await _max_gym_equips(session)
        bundle = compute_bundle(getattr(gym, "last_verified_at_cached", None), num, mx)
        data["freshness"] = bundle.freshness
        data["richness"] = bundle.richness
        data["score"] = bundle.score

    return GymDetailResponse.model_validate(data)


async def get_gym_detail_v1(
    session: AsyncSession, slug: str
) -> legacy_schemas.GymDetailResponse | None:
    """
    Router(app/routers) 向けのレガシー詳細レスポンスを返すサービス関数。
    - 見つからない場合は None を返し、router 側で 404 を返す方針。
    - スキーマは app/schemas.py の GymDetailResponse に準拠。
    """
    gym = await session.scalar(select(Gym).where(Gym.slug == slug))
    if not gym:
        return None

    eq_stmt = (
        select(
            Equipment.slug.label("equipment_slug"),
            Equipment.name.label("equipment_name"),
            Equipment.category,
            GymEquipment.availability,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
            GymEquipment.verification_status,
            GymEquipment.last_verified_at,
        )
        .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.category, Equipment.name)
    )
    rows = (await session.execute(eq_stmt)).all()

    equipments: list[legacy_schemas.EquipmentRow] = []
    updated_at: datetime | None = None
    for r in rows:
        # enum -> str
        availability = (
            r.availability.value if hasattr(r.availability, "value") else str(r.availability)
        )
        verification_status = (
            r.verification_status.value
            if hasattr(r.verification_status, "value")
            else str(r.verification_status)
        )
        equipments.append(
            legacy_schemas.EquipmentRow(
                equipment_slug=r.equipment_slug,
                equipment_name=r.equipment_name,
                category=r.category,
                availability=str(availability),
                count=r.count,
                max_weight_kg=r.max_weight_kg,
                verification_status=str(verification_status),
                last_verified_at=r.last_verified_at,
            )
        )
        if r.last_verified_at and (updated_at is None or r.last_verified_at > updated_at):
            updated_at = r.last_verified_at

    return legacy_schemas.GymDetailResponse(
        gym=legacy_schemas.GymBasic.model_validate(gym),
        equipments=equipments,
        sources=[],
        updated_at=updated_at,
    )


async def get_gym_detail_opt(
    session: AsyncSession, slug: str, include: str | None
) -> GymDetailResponse | None:
    """Optional-return wrapper for router-side 404 handling.

    Returns GymDetailResponse if found; otherwise None. Other HTTP errors from the
    underlying service are propagated.
    """
    try:
        return await get_gym_detail(session, slug, include)
    except HTTPException as exc:  # type: ignore[reportGeneralTypeIssues]
        if getattr(exc, "status_code", None) == 404:
            return None
        raise


class GymDetailService:
    """Service wrapper to enable DI via Depends in routers."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, slug: str, include: str | None) -> GymDetailResponse:
        return await get_gym_detail(self._session, slug, include)

    async def get_opt(self, slug: str, include: str | None) -> GymDetailResponse | None:
        return await get_gym_detail_opt(self._session, slug, include)
