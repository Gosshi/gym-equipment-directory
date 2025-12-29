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
    category: str | None = None  # gym, pool, court, hall, field, martial_arts, archery
    parsed_json: dict[str, Any] | None = None
    official_url: str | None = None
    source: AdminSourceRef
    fetched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminCandidateDetail(AdminCandidateItem):
    scraped_page: ScrapedPageInfo
    similar: list[SimilarGymInfo] | None = None
    gym_id: int | None = None


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
    official_url: str | None = None


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
    official_url: str | None = None


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


class ApprovalFieldChange(BaseModel):
    field: str
    before: Any | None = None
    after: Any | None = None


class AdminApproveGym(BaseModel):
    action: Literal["create", "update", "reuse", "skip"]
    gym_id: int | None = None
    slug: str | None = None
    canonical_id: str | None = None
    changes: list[ApprovalFieldChange] = Field(default_factory=list)
    after: dict[str, Any] | None = None


class AdminApproveEquipment(BaseModel):
    slug: str
    equipment_id: int | None = None
    action: Literal["insert", "merge", "skip"]
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    last_verified_at: str | None = None


class AdminApproveCandidateInfo(BaseModel):
    status: CandidateStatus
    approved_gym_slug: str | None = None


class AdminApproveResponse(BaseModel):
    candidate_id: int
    dry_run: bool
    gym: AdminApproveGym
    equipments: list[AdminApproveEquipment]
    candidate: AdminApproveCandidateInfo
    error: str | None = None


# ---- Bulk operations ----


class BulkApproveRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    dry_run: bool = False


class BulkRejectRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    reason: str = Field(min_length=1)
    dry_run: bool = False


class BulkApproveItem(BaseModel):
    candidate_id: int
    ok: bool
    error: str | None = None
    payload: AdminApproveResponse | None = None


class BulkRejectItem(BaseModel):
    candidate_id: int
    ok: bool
    error: str | None = None
    status: CandidateStatus | None = None


class BulkApproveResult(BaseModel):
    items: list[BulkApproveItem]
    success_count: int
    failure_count: int
    dry_run: bool
    audit_log_id: int | None = None


class BulkRejectResult(BaseModel):
    items: list[BulkRejectItem]
    success_count: int
    failure_count: int
    dry_run: bool
    audit_log_id: int | None = None
