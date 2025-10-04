from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.gym_candidate import CandidateStatus


class AdminSourceRef(BaseModel):
    id: int
    title: str | None = None
    url: str | None = None


class ScrapedPageInfo(BaseModel):
    url: str
    fetched_at: datetime
    http_status: int | None = None


class SimilarGymInfo(BaseModel):
    gym_id: int
    gym_slug: str
    gym_name: str


class AdminCandidateItem(BaseModel):
    id: int
    status: CandidateStatus
    name_raw: str
    address_raw: str | None = None
    pref_slug: str | None = None
    city_slug: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    parsed_json: dict[str, Any] | None = None
    source: AdminSourceRef
    fetched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminCandidateDetail(AdminCandidateItem):
    scraped_page: ScrapedPageInfo
    similar: list[SimilarGymInfo] | None = None


class AdminCandidateCreate(BaseModel):
    name_raw: str
    address_raw: str | None = None
    pref_slug: str
    city_slug: str
    latitude: float | None = None
    longitude: float | None = None
    parsed_json: dict[str, Any] | None = None
    official_url: str | None = None
    equipments: list[EquipmentAssign] | None = None


class AdminCandidatePatch(BaseModel):
    name_raw: str | None = None
    address_raw: str | None = None
    pref_slug: str | None = None
    city_slug: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    parsed_json: dict[str, Any] | None = None


class EquipmentAssign(BaseModel):
    slug: str
    availability: Literal["present", "absent", "unknown"] = "present"
    count: int | None = None
    max_weight_kg: int | None = None


class ApproveOverride(BaseModel):
    name: str | None = None
    pref_slug: str | None = None
    city_slug: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ApproveRequest(BaseModel):
    override: ApproveOverride | None = None
    equipments: list[EquipmentAssign] | None = None
    dry_run: bool = Field(default=False)


class GymUpsertPreview(BaseModel):
    slug: str
    name: str
    canonical_id: str
    pref_slug: str | None = None
    city_slug: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EquipmentUpsertSummary(BaseModel):
    inserted: int
    updated: int
    total: int


class ApproveSummary(BaseModel):
    gym: GymUpsertPreview
    equipments: EquipmentUpsertSummary


class ApprovePreview(BaseModel):
    preview: ApproveSummary


class ApproveResult(BaseModel):
    result: ApproveSummary


class AdminCandidateListResponse(BaseModel):
    items: list[AdminCandidateItem]
    next_cursor: str | None = None
    count: int


class RejectRequest(BaseModel):
    reason: str
