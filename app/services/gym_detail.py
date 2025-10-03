"""Gym detail use cases backed by repository interfaces."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app import schemas as legacy_schemas
from app.core.exceptions import NotFoundError
from app.dto import GymDetailDTO
from app.dto.mappers import assemble_gym_detail
from app.infra.unit_of_work import UnitOfWork
from app.models import Gym
from app.repositories.interfaces import (
    GymEquipmentBasicRow,
    GymEquipmentSummaryRow,
    GymImageRow,
)
from app.services.scoring import compute_bundle

UnitOfWorkFactory = Callable[[], UnitOfWork]


class GymDetailService:
    """Use cases for retrieving gym detail DTOs."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def get(self, slug: str, include: str | None) -> GymDetailDTO:
        async with self._uow_factory() as uow:
            return await get_gym_detail(uow, slug, include)

    async def get_opt(self, slug: str, include: str | None) -> GymDetailDTO | None:
        async with self._uow_factory() as uow:
            try:
                return await get_gym_detail(uow, slug, include)
            except NotFoundError:
                return None

    async def get_by_canonical_id(self, canonical_id: str, include: str | None) -> GymDetailDTO:
        async with self._uow_factory() as uow:
            return await get_gym_detail_by_canonical_id(uow, canonical_id, include)

    async def get_by_canonical_id_opt(
        self, canonical_id: str, include: str | None
    ) -> GymDetailDTO | None:
        async with self._uow_factory() as uow:
            try:
                return await get_gym_detail_by_canonical_id(uow, canonical_id, include)
            except NotFoundError:
                return None

    async def get_legacy(self, slug: str) -> legacy_schemas.GymDetailResponse | None:
        async with self._uow_factory() as uow:
            return await get_gym_detail_v1(uow, slug)


async def get_gym_detail(uow: UnitOfWork, slug: str, include: str | None) -> GymDetailDTO:
    gym = await uow.gyms.get_by_slug(slug)
    if gym is None:
        raise NotFoundError("gym not found")
    return await _build_gym_detail(uow, gym, include)


async def get_gym_detail_by_canonical_id(
    uow: UnitOfWork, canonical_id: str, include: str | None
) -> GymDetailDTO:
    gym = await uow.gyms.get_by_canonical_id(canonical_id)
    if gym is None:
        raise NotFoundError("gym not found")
    return await _build_gym_detail(uow, gym, include)


async def _build_gym_detail(uow: UnitOfWork, gym: Gym, include: str | None) -> GymDetailDTO:
    gym_id = int(getattr(gym, "id", 0))

    equipments_basic = await uow.gyms.fetch_equipment_basic(gym_id)
    equipment_summaries = await uow.gyms.fetch_equipment_summaries(gym_id)
    images = await uow.gyms.fetch_images(gym_id)

    equipments_list = [_equipment_basic_to_dict(row) for row in equipments_basic]
    gym_equipments_list = [_equipment_summary_to_dict(row) for row in equipment_summaries]
    images_list = [_image_row_to_dict(row) for row in images]

    freshness = richness = score = None
    if include == "score":
        count = await uow.gyms.count_gym_equipments(gym_id)
        max_count = await uow.gyms.max_gym_equipments()
        bundle = compute_bundle(getattr(gym, "last_verified_at_cached", None), count, max_count)
        freshness = bundle.freshness
        richness = bundle.richness
        score = bundle.score

    return assemble_gym_detail(
        gym,
        equipments_list,
        gym_equipments_list,
        images_list,
        updated_at=getattr(gym, "updated_at", None),
        freshness=freshness,
        richness=richness,
        score=score,
    )


async def get_gym_detail_v1(uow: UnitOfWork, slug: str) -> legacy_schemas.GymDetailResponse | None:
    requested_slug = slug
    gym = await uow.gyms.get_by_slug(slug)
    if gym is None:
        gym = await uow.gyms.get_by_slug_from_history(slug)
        if gym is None:
            return None

    canonical_slug = str(getattr(gym, "slug", requested_slug))
    meta: legacy_schemas.GymDetailMeta | None = None
    if canonical_slug != requested_slug:
        meta = legacy_schemas.GymDetailMeta(redirect=True)

    gym_id = int(getattr(gym, "id", 0))
    rows = await uow.gyms.fetch_equipment_summaries(gym_id)

    equipments: list[legacy_schemas.EquipmentRow] = []
    updated_at: datetime | None = None

    for row in rows:
        equipments.append(
            legacy_schemas.EquipmentRow(
                equipment_slug=row.slug,
                equipment_name=row.name,
                category=row.category,
                availability=str(row.availability or ""),
                count=row.count,
                max_weight_kg=row.max_weight_kg,
                verification_status=str(row.verification_status or ""),
                last_verified_at=row.last_verified_at,
            )
        )
        if row.last_verified_at and (updated_at is None or row.last_verified_at > updated_at):
            updated_at = row.last_verified_at

    return legacy_schemas.GymDetailResponse(
        gym=legacy_schemas.GymBasic.model_validate(gym),
        equipments=equipments,
        sources=[],
        updated_at=updated_at,
        official_url=getattr(gym, "official_url", None),
        requested_slug=requested_slug,
        canonical_slug=canonical_slug,
        meta=meta,
    )


async def get_gym_detail_opt(
    uow: UnitOfWork, slug: str, include: str | None
) -> GymDetailDTO | None:
    try:
        return await get_gym_detail(uow, slug, include)
    except NotFoundError:
        return None


def _equipment_basic_to_dict(row: GymEquipmentBasicRow) -> dict[str, object | None]:
    return {
        "equipment_slug": row.equipment_slug,
        "equipment_name": row.equipment_name,
        "category": row.category,
        "count": row.count,
        "max_weight_kg": row.max_weight_kg,
    }


def _equipment_summary_to_dict(row: GymEquipmentSummaryRow) -> dict[str, object | None]:
    return {
        "slug": row.slug,
        "name": row.name,
        "availability": str(row.availability or ""),
        "verification_status": str(row.verification_status or ""),
        "last_verified_at": row.last_verified_at,
        "source": row.source,
    }


def _image_row_to_dict(row: GymImageRow) -> dict[str, object | None]:
    return {
        "url": row.url,
        "source": row.source,
        "verified": row.verified,
        "created_at": row.created_at,
    }
