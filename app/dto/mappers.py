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
from app.dto.gym import CourtItemDTO, PoolItemDTO
from app.models import Equipment, Gym, GymImage


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    # Guard against sentinel dates (e.g. < 1970) used historically.
    if hasattr(dt, "year") and dt.year < 1970:
        return None
    return dt.isoformat()


def _resolve_categories(gym: Gym) -> list[str]:
    """Resolve categories with fallback logic for legacy fields."""
    # 1. Primary source: categories column
    categories = getattr(gym, "categories", None)
    if categories and len(categories) > 0:
        return categories

    # 2. Secondary source: parsed_json.meta.categories
    parsed = getattr(gym, "parsed_json", {}) or {}
    meta = parsed.get("meta", {})
    json_categories = meta.get("categories")
    if json_categories and isinstance(json_categories, list) and len(json_categories) > 0:
        return json_categories

    # 3. Fallback: legacy category column
    legacy_category = getattr(gym, "category", None)
    if legacy_category:
        return [legacy_category]

    # 4. Fallback: legacy parsed_json.meta.category
    meta_category = meta.get("category")
    if meta_category:
        return [meta_category]

    # 5. Default empty (frontend defaults to "gym")
    return []


def map_gym_to_summary(
    gym: Gym,
    *,
    last_verified_at: datetime | None,
    score: float | None,
    freshness_score: float | None = None,
    richness_score: float | None = None,
    distance_km: float | None = None,
) -> GymSummaryDTO:
    """Map Gym ORM object to GymSummaryDTO.

    Handles fallback logic for fields that might be missing or structured differently
    in JSON vs columns.
    """
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
        categories=_resolve_categories(gym),
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

    # Extract categories - unified approach
    # Priority: parsed_json.categories > gym.categories > meta.category wrapped in list
    categories_raw = getattr(gym, "categories", None)
    if parsed_json.get("categories") and isinstance(parsed_json.get("categories"), list):
        categories = parsed_json.get("categories")
    elif categories_raw and isinstance(categories_raw, list) and len(categories_raw) > 0:
        categories = categories_raw
    elif meta.get("categories") and isinstance(meta.get("categories"), list):
        categories = meta.get("categories")
    elif meta.get("category"):
        categories = [meta.get("category")]
    else:
        categories = []

    # Helper to normalize data that could be a list or dict
    def _normalize_to_dict(data: Any) -> dict[str, Any]:
        """Normalize data to a dict, taking first element if it's a list."""
        if isinstance(data, list) and len(data) > 0:
            return data[0] if isinstance(data[0], dict) else {}
        if isinstance(data, dict):
            return data
        return {}

    def _normalize_to_list(data: Any) -> list[dict[str, Any]]:
        """Normalize data to a list of dicts."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    # Extract category-specific fields from meta or parsed_json root
    # Try meta first, then fallback to parsed_json root for category-specific objects
    # Pool - may be a dict or a list of dicts
    pool_raw = meta.get("pool") or parsed_json.get("pool")
    pool_data = _normalize_to_dict(pool_raw)
    pool_list = _normalize_to_list(pool_raw)
    pool_lanes = meta.get("lanes") or pool_data.get("lanes")
    pool_length_m = meta.get("length_m") or pool_data.get("length_m")
    pool_heated = meta.get("heated") if meta.get("heated") is not None else pool_data.get("heated")
    # Build pools array
    pools = [
        PoolItemDTO(
            lanes=p.get("lanes"),
            length_m=p.get("length_m"),
            heated=p.get("heated"),
        )
        for p in pool_list
    ]

    # Court - may be a dict or a list of dicts
    court_raw = meta.get("court") or parsed_json.get("court")
    court_data = _normalize_to_dict(court_raw)
    court_list = _normalize_to_list(court_raw)
    court_type = meta.get("court_type") or court_data.get("court_type")
    court_count = meta.get("courts") or court_data.get("courts")
    # Handle court_count that might be an array (new LLM format)
    if isinstance(court_count, list):
        court_count = None  # Will be derived from courts array
    court_surface = meta.get("surface") or court_data.get("surface")
    # Check if court is in categories list
    is_court_category = "court" in categories
    court_lighting = (
        meta.get("lighting")
        if is_court_category and meta.get("lighting") is not None
        else court_data.get("lighting")
        if is_court_category
        else None
    )
    # Build courts array - check for new format (court_data.courts is array) first
    courts_inner = court_data.get("courts")
    if isinstance(courts_inner, list) and len(courts_inner) > 0:
        # New format: court.courts is array of {court_type, count}
        courts = [
            CourtItemDTO(
                court_type=c.get("court_type"),
                courts=c.get("count") or c.get("courts"),  # Support both 'count' and 'courts'
                surface=court_data.get("surface"),  # Shared surface from parent
                lighting=court_data.get("lighting"),  # Shared lighting from parent
            )
            for c in courts_inner
            if isinstance(c, dict)
        ]
    else:
        # Old format: court_list is array of court objects
        courts = [
            CourtItemDTO(
                court_type=c.get("court_type"),
                courts=c.get("courts") or c.get("count"),
                surface=c.get("surface"),
                lighting=c.get("lighting"),
            )
            for c in court_list
        ]

    # Hall - may be a dict or a list of dicts
    hall_raw = meta.get("hall") or parsed_json.get("hall")
    hall_data = _normalize_to_dict(hall_raw)
    hall_sports = meta.get("sports") or hall_data.get("sports", [])
    if not isinstance(hall_sports, list):
        hall_sports = []
    hall_area_sqm = meta.get("area_sqm") or hall_data.get("area_sqm")

    # Field - may be a dict or a list of dicts
    field_raw = meta.get("field") or parsed_json.get("field")
    field_data = _normalize_to_dict(field_raw)
    field_type = meta.get("field_type") or field_data.get("field_type")
    field_count = meta.get("fields") or field_data.get("fields")
    # Check if field is in categories list
    is_field_category = "field" in categories
    field_lighting = (
        meta.get("lighting")
        if is_field_category and meta.get("lighting") is not None
        else field_data.get("lighting")
        if is_field_category
        else None
    )

    # Archery / Martial Arts - may be a dict or a list of dicts
    archery_raw = meta.get("archery") or parsed_json.get("archery")
    martial_arts_raw = meta.get("martial_arts") or parsed_json.get("martial_arts")
    archery_data = _normalize_to_dict(archery_raw) or _normalize_to_dict(martial_arts_raw)
    archery_type = archery_data.get("archery_type")
    archery_rooms = archery_data.get("rooms")

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
        # Categories (unified field)
        categories=categories,
        facility_meta=meta,
        pool_lanes=pool_lanes,
        pool_length_m=pool_length_m,
        pool_heated=pool_heated,
        pools=pools,
        court_type=court_type,
        court_count=court_count,
        court_surface=court_surface,
        court_lighting=court_lighting,
        courts=courts,
        hall_sports=hall_sports,
        hall_area_sqm=hall_area_sqm,
        field_type=field_type,
        field_count=field_count,
        field_lighting=field_lighting,
        archery_type=archery_type,
        archery_rooms=archery_rooms,
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
