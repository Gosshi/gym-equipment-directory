"""Utilities to map ORM/domain objects into DTOs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from app.dto import (
    EquipmentMasterDTO,
    GymDetailDTO,
    GymEquipmentLineDTO,
    GymEquipmentSummaryDTO,
    GymImageDTO,
    GymSummaryDTO,
)
from app.models import Equipment, Gym, GymImage


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    # Guard against sentinel dates (e.g. < 1970) used historically.
    if hasattr(dt, "year") and dt.year < 1970:
        return None
    return dt.isoformat()


def map_gym_to_summary(
    gym: Gym,
    *,
    last_verified_at: datetime | None,
    score: float | None,
    freshness_score: float | None = None,
    richness_score: float | None = None,
    distance_km: float | None = None,
) -> GymSummaryDTO:
    return GymSummaryDTO(
        id=int(getattr(gym, "id", 0)),
        slug=str(getattr(gym, "slug", "") or ""),
        canonical_id=str(getattr(gym, "canonical_id", "") or ""),
        name=str(getattr(gym, "name", "") or ""),
        pref=str(getattr(gym, "pref", "") or ""),
        city=str(getattr(gym, "city", "") or ""),
        last_verified_at=_iso(last_verified_at),
        score=score,
        freshness_score=freshness_score,
        richness_score=richness_score,
        distance_km=distance_km,
    )


def map_equipment_row(row: Mapping[str, Any]) -> GymEquipmentLineDTO:
    return GymEquipmentLineDTO(
        equipment_slug=str(row.get("equipment_slug")),
        equipment_name=str(row.get("equipment_name")),
        category=row.get("category"),
        count=row.get("count"),
        max_weight_kg=row.get("max_weight_kg"),
    )


def map_equipment_summary(row: Mapping[str, Any]) -> GymEquipmentSummaryDTO:
    return GymEquipmentSummaryDTO(
        slug=str(row.get("slug")),
        name=str(row.get("name")),
        category=row.get("category"),
        count=row.get("count"),
        max_weight_kg=row.get("max_weight_kg"),
        availability=str(row.get("availability")),
        verification_status=str(row.get("verification_status")),
        last_verified_at=row.get("last_verified_at"),
        source=row.get("source"),
    )


def map_gym_image(row: Mapping[str, Any]) -> GymImageDTO:
    return GymImageDTO(
        url=str(row.get("url")),
        source=row.get("source"),
        verified=bool(row.get("verified", False)),
        created_at=row.get("created_at"),
    )


def assemble_gym_detail(
    gym: Gym,
    equipments: Iterable[Mapping[str, Any]],
    equipment_summaries: Iterable[Mapping[str, Any]],
    images: Iterable[Mapping[str, Any]],
    *,
    updated_at: datetime | None,
    freshness: float | None = None,
    richness: float | None = None,
    score: float | None = None,
) -> GymDetailDTO:
    return GymDetailDTO(
        id=int(getattr(gym, "id", 0)),
        slug=str(getattr(gym, "slug", "")),
        canonical_id=str(getattr(gym, "canonical_id", "")),
        name=str(getattr(gym, "name", "")),
        city=str(getattr(gym, "city", "")),
        pref=str(getattr(gym, "pref", "")),
        address=getattr(gym, "address", None),
        latitude=getattr(gym, "latitude", None),
        longitude=getattr(gym, "longitude", None),
        equipments=[map_equipment_row(r) for r in equipments],
        gym_equipments=[map_equipment_summary(r) for r in equipment_summaries],
        images=[map_gym_image(r) for r in images],
        updated_at=_iso(updated_at),
        freshness=freshness,
        richness=richness,
        score=score,
    )


def map_equipment_master(row: Mapping[str, Any] | Equipment) -> EquipmentMasterDTO:
    if isinstance(row, Equipment):
        return EquipmentMasterDTO.model_validate(row)
    return EquipmentMasterDTO(
        id=int(row.get("id", 0)),
        slug=str(row.get("slug", "")),
        name=str(row.get("name", "")),
        category=row.get("category"),
    )


def map_gym_image_model(image: GymImage) -> GymImageDTO:
    return GymImageDTO(
        url=str(getattr(image, "url", "")),
        source=getattr(image, "source", None),
        verified=bool(getattr(image, "verified", False)),
        created_at=getattr(image, "created_at", None),
    )
