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
        official_url=getattr(gym, "official_url", None),
        last_verified_at=_iso(last_verified_at),
        score=score,
        freshness_score=freshness_score,
        richness_score=richness_score,
        distance_km=distance_km,
        tags=list(getattr(gym, "parsed_json", {}).get("tags", [])),
        category=getattr(gym, "category", None),
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
        availability=row.get("availability"),
        verification_status=row.get("verification_status"),
        last_verified_at=row.get("last_verified_at"),
        source=row.get("source"),
    )


def map_gym_image(row: Mapping[str, Any]) -> GymImageDTO:
    return GymImageDTO(
        url=str(row.get("url")),
        alt=row.get("alt"),
        sort_order=row.get("sort_order"),
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
    parsed_json = getattr(gym, "parsed_json", None) or {}

    # Data may be in parsed_json.meta (new structure) or parsed_json root (old structure)
    meta = parsed_json.get("meta", {})

    # Extract hours from parsed_json (check meta first, then root)
    hours_data = meta.get("hours") or parsed_json.get("hours")
    opening_hours: str | None = None
    if hours_data:
        if isinstance(hours_data, dict):
            open_time = hours_data.get("open")
            close_time = hours_data.get("close")
            if open_time and close_time:
                # Format: 900 -> "9:00", 2100 -> "21:00"
                def fmt_time(t: int) -> str:
                    h, m = divmod(t, 100)
                    return f"{h}:{m:02d}"

                opening_hours = f"{fmt_time(open_time)}〜{fmt_time(close_time)}"
        elif isinstance(hours_data, str):
            opening_hours = hours_data

    # Extract fee from parsed_json (check meta first, then root)
    fee_data = meta.get("fee") or parsed_json.get("fee")
    fees: str | None = None
    if fee_data:
        if isinstance(fee_data, int):
            fees = f"{fee_data}円"
        elif isinstance(fee_data, dict):
            # Japanese key mapping for better readability
            fee_key_ja = {
                "per_hour": "1時間",
                "per_2hours": "2時間",
                "per_session": "1回",
                "adult": "大人",
                "child": "子供",
                "senior": "シニア",
                "student": "学生",
                "youth": "青年",
                "monthly": "月額",
                "yearly": "年額",
            }
            parts = []
            for key, value in fee_data.items():
                if isinstance(value, int):
                    label = fee_key_ja.get(key, key)
                    parts.append(f"{label}: {value}円")
            if parts:
                fees = " / ".join(parts)
        elif isinstance(fee_data, str):
            fees = fee_data

    # Extract category (legacy) and categories (new array)
    category = meta.get("category") or getattr(gym, "category", None)

    # Get categories array from gym model, fallback to single category wrapped in list
    categories_raw = getattr(gym, "categories", None)
    if categories_raw and isinstance(categories_raw, list):
        categories = categories_raw
    elif category:
        categories = [category]
    else:
        categories = []

    # Extract category-specific fields from meta
    # Pool
    pool_lanes = meta.get("lanes")
    pool_length_m = meta.get("length_m")
    pool_heated = meta.get("heated")

    # Court
    court_type = meta.get("court_type")
    court_count = meta.get("courts")
    court_surface = meta.get("surface")
    court_lighting = meta.get("lighting") if category == "court" else None

    # Hall
    hall_sports = meta.get("sports", [])
    if not isinstance(hall_sports, list):
        hall_sports = []
    hall_area_sqm = meta.get("area_sqm")

    # Field
    field_type = meta.get("field_type")
    field_count = meta.get("fields")
    field_lighting = meta.get("lighting") if category == "field" else None

    return GymDetailDTO(
        id=int(getattr(gym, "id", 0)),
        slug=str(getattr(gym, "slug", "")),
        canonical_id=str(getattr(gym, "canonical_id", "")),
        name=str(getattr(gym, "name", "")),
        city=str(getattr(gym, "city", "")),
        pref=str(getattr(gym, "pref", "")),
        address=getattr(gym, "address", None),
        official_url=getattr(gym, "official_url", None) or parsed_json.get("official_url"),
        opening_hours=opening_hours,
        fees=fees,
        latitude=getattr(gym, "latitude", None),
        longitude=getattr(gym, "longitude", None),
        last_verified_at_cached=_iso(getattr(gym, "last_verified_at_cached", None)),
        equipments=[map_equipment_row(r) for r in equipments],
        gym_equipments=[map_equipment_summary(r) for r in equipment_summaries],
        images=[map_gym_image(r) for r in images],
        updated_at=_iso(updated_at),
        freshness=freshness,
        richness=richness,
        score=score,
        tags=list(parsed_json.get("tags", [])),
        # Category-specific fields
        category=category,
        categories=categories,
        facility_meta=meta,
        pool_lanes=pool_lanes,
        pool_length_m=pool_length_m,
        pool_heated=pool_heated,
        court_type=court_type,
        court_count=court_count,
        court_surface=court_surface,
        court_lighting=court_lighting,
        hall_sports=hall_sports,
        hall_area_sqm=hall_area_sqm,
        field_type=field_type,
        field_count=field_count,
        field_lighting=field_lighting,
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
        alt=getattr(image, "alt", None),
        sort_order=getattr(image, "sort_order", None),
        source=getattr(image, "source", None),
        verified=bool(getattr(image, "verified", False)),
        created_at=getattr(image, "created_at", None),
    )
