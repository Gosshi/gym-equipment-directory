from __future__ import annotations

import base64
import json
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateStatus,
    Equipment,
    Gym,
    GymCandidate,
    GymEquipment,
    ScrapedPage,
    Source,
)
from app.models.gym_equipment import Availability, VerificationStatus
from app.schemas.admin_candidates import (
    AdminCandidatePatch,
    ApproveOverride,
    ApprovePreview,
    ApproveRequest,
    ApproveResult,
    ApproveSummary,
    EquipmentAssign,
    EquipmentUpsertSummary,
    GymUpsertPreview,
)


@dataclass
class CandidateRow:
    candidate: GymCandidate
    page: ScrapedPage
    source: Source | None


@dataclass
class CandidateDetailRow(CandidateRow):
    similar: list[Gym]


class CandidateServiceError(ValueError):
    """Raised when inputs are invalid."""


def _encode_cursor(payload: dict[str, int]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(token: str) -> dict[str, int]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise CandidateServiceError("invalid cursor") from exc
    if not isinstance(data, dict) or "id" not in data:
        raise CandidateServiceError("invalid cursor")
    cursor_id = data.get("id")
    if not isinstance(cursor_id, int):
        raise CandidateServiceError("invalid cursor")
    return {"id": cursor_id}


def _as_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)



def _strip_nul(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\x00", "")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff\s-]", "", normalized)
    lowered = cleaned.lower()
    tokens = re.split(r"[\s_-]+", lowered)
    slug = "-".join(filter(None, tokens))
    return slug[:64].strip("-")


def _build_slug(name: str, address: str | None, city: str | None, pref: str | None) -> str:
    parts = [name]
    if city:
        parts.append(city)
    if pref:
        parts.append(pref)
    if address:
        parts.append(address)
    slug = _slugify("-".join(parts))
    if not slug:
        raise CandidateServiceError("failed to generate slug")
    return slug


async def _base_query(
    session: AsyncSession,
) -> Select[tuple[GymCandidate, ScrapedPage, Source | None]]:
    stmt = (
        select(GymCandidate, ScrapedPage, Source)
        .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
        .join(Source, ScrapedPage.source_id == Source.id, isouter=True)
    )
    return stmt


def _apply_filters(
    stmt: Select[tuple[GymCandidate, ScrapedPage, Source | None]],
    *,
    status: CandidateStatus | None,
    source: str | None,
    q: str | None,
    pref: str | None,
    city: str | None,
    cursor: dict[str, int] | None,
) -> Select[tuple[GymCandidate, ScrapedPage, Source | None]]:
    conditions = []
    if status:
        conditions.append(GymCandidate.status == status)
    if source:
        term = f"%{source.strip()}%"
        src_cond = [Source.title.ilike(term)]
        if source.strip().isdigit():
            src_cond.append(Source.id == int(source.strip()))
        conditions.append(or_(*src_cond))
    if q:
        conditions.append(GymCandidate.name_raw.ilike(f"%{q.strip()}%"))
    if pref:
        conditions.append(GymCandidate.pref_slug == pref.strip())
    if city:
        conditions.append(GymCandidate.city_slug == city.strip())
    if cursor:
        conditions.append(GymCandidate.id < cursor["id"])
    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt.order_by(GymCandidate.id.desc())


async def list_candidates(
    session: AsyncSession,
    *,
    status: CandidateStatus | None,
    source: str | None,
    q: str | None,
    pref: str | None,
    city: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[CandidateRow], str | None]:
    if limit < 1 or limit > 100:
        raise CandidateServiceError("limit must be between 1 and 100")
    decoded_cursor = _decode_cursor(cursor) if cursor else None
    stmt = await _base_query(session)
    stmt = _apply_filters(
        stmt,
        status=status,
        source=source,
        q=q,
        pref=pref,
        city=city,
        cursor=decoded_cursor,
    ).limit(limit + 1)
    result = await session.execute(stmt)
    rows = result.all()
    has_next = len(rows) > limit
    sliced = rows[:limit]
    items = [CandidateRow(candidate=row[0], page=row[1], source=row[2]) for row in sliced]
    next_cursor = None
    if has_next and items:
        next_cursor = _encode_cursor({"id": int(items[-1].candidate.id)})
    return items, next_cursor


async def _fetch_candidate_row(session: AsyncSession, candidate_id: int) -> CandidateRow:
    stmt = await _base_query(session)
    stmt = stmt.where(GymCandidate.id == candidate_id)
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise LookupError("candidate not found")
    return CandidateRow(candidate=row[0], page=row[1], source=row[2])


async def get_candidate_detail(session: AsyncSession, candidate_id: int) -> CandidateDetailRow:
    row = await _fetch_candidate_row(session, candidate_id)
    candidate = row.candidate
    similar_stmt = select(Gym).limit(5)
    conditions = []
    if candidate.pref_slug:
        conditions.append(Gym.pref == candidate.pref_slug)
    if candidate.city_slug:
        conditions.append(Gym.city == candidate.city_slug)
    if candidate.name_raw:
        conditions.append(Gym.name.ilike(f"%{candidate.name_raw.strip()}%"))
    if conditions:
        similar_stmt = similar_stmt.where(and_(*conditions))
    similar_stmt = similar_stmt.order_by(Gym.id.asc()).limit(5)
    similar_result = await session.execute(similar_stmt)
    similar = list(similar_result.scalars().all())
    return CandidateDetailRow(
        candidate=row.candidate,
        page=row.page,
        source=row.source,
        similar=similar,
    )


async def patch_candidate(
    session: AsyncSession, candidate_id: int, patch: AdminCandidatePatch
) -> CandidateRow:
    candidate = await session.get(GymCandidate, candidate_id)
    if not candidate:
        raise LookupError("candidate not found")
    data = patch.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(candidate, field, value)
    await session.flush()
    await session.commit()
    return await _fetch_candidate_row(session, candidate_id)


def _collect_equipment_assigns(
    request_assigns: list[EquipmentAssign] | None, parsed_json: dict[str, Any] | None
) -> list[EquipmentAssign]:
    if request_assigns:
        assigns = request_assigns
    else:
        assigns = []
        equipments = []
        if parsed_json and isinstance(parsed_json, dict):
            equipments = parsed_json.get("equipments") or []
        for slug in equipments:
            if isinstance(slug, str) and slug:
                assigns.append(EquipmentAssign(slug=slug))
    deduped: dict[str, EquipmentAssign] = {}
    for assign in assigns:
        key = assign.slug
        if key not in deduped:
            deduped[key] = assign
    return list(deduped.values())


async def _load_equipment_map(
    session: AsyncSession, assigns: Iterable[EquipmentAssign]
) -> dict[str, Equipment]:
    slugs = {a.slug for a in assigns}
    if not slugs:
        return {}
    stmt = select(Equipment).where(Equipment.slug.in_(slugs))
    result = await session.execute(stmt)
    items = {eq.slug: eq for eq in result.scalars().all()}
    missing = slugs.difference(items.keys())
    if missing:
        raise CandidateServiceError(f"unknown equipment slug(s): {', '.join(sorted(missing))}")
    return items


def _gym_to_preview(gym: Gym) -> GymUpsertPreview:
    return GymUpsertPreview(
        slug=gym.slug,
        name=gym.name,
        pref_slug=gym.pref,
        city_slug=gym.city,
        address=gym.address,
        latitude=gym.latitude,
        longitude=gym.longitude,
    )


def _compose_gym_preview(
    existing: Gym | None,
    *,
    slug: str,
    name: str,
    pref_slug: str,
    city_slug: str,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
) -> GymUpsertPreview:
    lat = latitude
    lon = longitude
    if existing:
        if existing.latitude is not None:
            lat = existing.latitude
        if existing.longitude is not None:
            lon = existing.longitude
    return GymUpsertPreview(
        slug=slug,
        name=name,
        pref_slug=pref_slug,
        city_slug=city_slug,
        address=address,
        latitude=lat,
        longitude=lon,
    )


async def _apply_gym_upsert(
    session: AsyncSession,
    existing: Gym | None,
    *,
    slug: str,
    name: str,
    pref_slug: str,
    city_slug: str,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
) -> Gym:
    if existing is None:
        gym = Gym(
            slug=slug,
            name=name,
            pref=pref_slug,
            city=city_slug,
            address=address,
            latitude=latitude,
            longitude=longitude,
        )
        session.add(gym)
        await session.flush()
        return gym
    gym = existing
    gym.name = name
    gym.pref = pref_slug
    gym.city = city_slug
    gym.address = address
    if gym.latitude is None and latitude is not None:
        gym.latitude = latitude
    if gym.longitude is None and longitude is not None:
        gym.longitude = longitude
    await session.flush()
    return gym


async def ensure_equipment_links(
    session: AsyncSession,
    gym: Gym | None,
    assigns: Sequence[EquipmentAssign],
    *,
    apply_changes: bool,
) -> tuple[EquipmentUpsertSummary, datetime | None]:
    if not assigns:
        return EquipmentUpsertSummary(inserted=0, updated=0, total=0), None
    if apply_changes and (gym is None or gym.id is None):
        raise CandidateServiceError("gym must be persisted before linking equipments")
    equipment_map = await _load_equipment_map(session, assigns)
    equipment_ids = [equipment_map[a.slug].id for a in assigns]
    existing_map: dict[int, GymEquipment] = {}
    if gym and gym.id:
        stmt = select(GymEquipment).where(
            GymEquipment.gym_id == gym.id,
            GymEquipment.equipment_id.in_(equipment_ids),
        )
        result = await session.execute(stmt)
        existing_map = {row.equipment_id: row for row in result.scalars().all()}
    inserted = 0
    updated = 0
    timestamps: list[datetime] = []
    now = datetime.now(UTC)
    now_naive = _as_naive_utc(now)
    for assign in assigns:
        equipment = equipment_map[assign.slug]
        existing = existing_map.get(equipment.id)
        availability = Availability(assign.availability)
        if existing is None:
            inserted += 1
            if apply_changes:
                link = GymEquipment(
                    gym_id=gym.id if gym else None,
                    equipment_id=equipment.id,
                    availability=availability,
                    count=assign.count,
                    max_weight_kg=assign.max_weight_kg,
                    verification_status=VerificationStatus.user_verified,
                    last_verified_at=now_naive,
                )
                session.add(link)
            timestamps.append(now_naive)
        else:
            updated += 1
            if apply_changes:
                existing.availability = availability
                if assign.count is not None:
                    existing.count = assign.count
                if assign.max_weight_kg is not None:
                    existing.max_weight_kg = assign.max_weight_kg
                existing.verification_status = VerificationStatus.user_verified
                existing.last_verified_at = now_naive
            timestamps.append(now_naive)
    if apply_changes:
        await session.flush()
    summary = EquipmentUpsertSummary(
        inserted=inserted,
        updated=updated,
        total=inserted + updated,
    )
    latest = max(timestamps) if timestamps else None
    return summary, latest


async def approve_candidate(
    session: AsyncSession, candidate_id: int, request: ApproveRequest
) -> ApprovePreview | ApproveResult:
    row = await _fetch_candidate_row(session, candidate_id)
    candidate = row.candidate
    override = request.override or ApproveOverride()
    candidate_name = _strip_nul(candidate.name_raw)
    candidate_pref = _strip_nul(candidate.pref_slug)
    candidate_city = _strip_nul(candidate.city_slug)
    candidate_address = _strip_nul(candidate.address_raw)
    override_name = _strip_nul(override.name)
    override_pref = _strip_nul(override.pref_slug)
    override_city = _strip_nul(override.city_slug)
    override_address = _strip_nul(override.address)
    name = override_name or candidate_name
    pref_slug = override_pref or candidate_pref
    city_slug = override_city or candidate_city
    address = override_address or candidate_address
    latitude = override.latitude if override.latitude is not None else candidate.latitude
    longitude = override.longitude if override.longitude is not None else candidate.longitude
    if not name:
        raise CandidateServiceError("name is required")
    if not pref_slug:
        raise CandidateServiceError("pref_slug is required")
    if not city_slug:
        raise CandidateServiceError("city_slug is required")
    slug = _build_slug(name, address, city_slug, pref_slug)
    assigns = _collect_equipment_assigns(request.equipments, candidate.parsed_json)
    existing_stmt = select(Gym).where(Gym.slug == slug)
    existing_result = await session.execute(existing_stmt)
    existing_gym = existing_result.scalars().first()
    preview_gym = _compose_gym_preview(
        existing_gym,
        slug=slug,
        name=name,
        pref_slug=pref_slug,
        city_slug=city_slug,
        address=address,
        latitude=latitude,
        longitude=longitude,
    )
    preview_summary, preview_latest = await ensure_equipment_links(
        session,
        existing_gym,
        assigns,
        apply_changes=False,
    )
    if request.dry_run:
        return ApprovePreview(preview=ApproveSummary(gym=preview_gym, equipments=preview_summary))
    try:
        gym = await _apply_gym_upsert(
            session,
            existing_gym,
            slug=slug,
            name=name,
            pref_slug=pref_slug,
            city_slug=city_slug,
            address=address,
            latitude=preview_gym.latitude,
            longitude=preview_gym.longitude,
        )
    except IntegrityError as exc:  # pragma: no cover - handled by caller
        raise exc
    summary, latest = await ensure_equipment_links(
        session,
        gym,
        assigns,
        apply_changes=True,
    )
    latest_cached = _as_naive_utc(latest)
    preview_cached = _as_naive_utc(preview_latest)
    if latest_cached:
        gym.last_verified_at_cached = latest_cached
    elif preview_cached:
        gym.last_verified_at_cached = preview_cached
    candidate.status = CandidateStatus.approved
    await session.flush()
    await session.commit()
    return ApproveResult(result=ApproveSummary(gym=_gym_to_preview(gym), equipments=summary))


async def reject_candidate(session: AsyncSession, candidate_id: int, reason: str) -> CandidateRow:
    candidate = await session.get(GymCandidate, candidate_id)
    if not candidate:
        raise LookupError("candidate not found")
    candidate.status = CandidateStatus.rejected
    payload = dict(candidate.parsed_json or {})
    payload["rejection_reason"] = reason
    candidate.parsed_json = payload
    await session.flush()
    await session.commit()
    return await _fetch_candidate_row(session, candidate_id)
