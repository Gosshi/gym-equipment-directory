from __future__ import annotations

import base64
import json
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

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
    SourceType,
)
from app.models.gym_equipment import Availability, VerificationStatus
from app.schemas.admin_candidates import (
    AdminCandidateCreate,
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
from app.services.canonical import make_canonical_id
from app.services.scrape_utils import try_scrape_official_url
from app.services.slug_generator import build_hierarchical_slug
from app.services.slug_history import set_current_slug

_ARTICLE_PAT = re.compile(
    r"/introduction/(?:post_|tr_detail\.html|trainingmachine\.html|notes\.html)$"
)
_INTRO_BASE_PAT = re.compile(r"(/sports_center\d+/introduction)/?")
_CENTER_NO_PAT = re.compile(r"/sports_center(\d+)/")
_ZW_CHARS = re.compile(r"[\u200B-\u200D\uFEFF]")
_GENERIC_TITLES = {"トレーニングマシンの紹介", "トレーニングルーム", "利用上の注意"}


@dataclass
class CandidateRow:
    candidate: GymCandidate
    page: ScrapedPage
    source: Source | None


@dataclass
class CandidateDetailRow(CandidateRow):
    similar: list[Gym]
    gym_id: int | None = None


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


def _slugify(value: str) -> str:
    """Convert Japanese text to SEO-friendly romaji slug.

    Uses pykakasi to convert kanji/kana to romaji, then normalizes.
    """
    try:
        from pykakasi import kakasi

        kks = kakasi()
        # Convert Japanese to romaji
        result = kks.convert(value)
        romaji = "".join([item["hepburn"] for item in result])
    except ImportError:
        # Fallback if pykakasi not available
        romaji = value

    normalized = unicodedata.normalize("NFKC", romaji)
    # Remove non-alphanumeric characters except hyphens and spaces
    cleaned = re.sub(r"[^0-9A-Za-z\s-]", "", normalized)
    lowered = cleaned.lower()
    tokens = re.split(r"[\s_-]+", lowered)
    slug = "-".join(filter(None, tokens))
    return slug[:64].strip("-")


def _sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = value.replace("\x00", "")
    sanitized = _ZW_CHARS.sub("", sanitized)
    sanitized = unicodedata.normalize("NFKC", sanitized).strip()
    return sanitized or None


def _is_generic_title(name: str) -> bool:
    compact = name.replace(" ", "")
    return any(compact.startswith(title.replace(" ", "")) for title in _GENERIC_TITLES)


def _build_slug(name: str, address: str | None, city: str | None, pref: str | None) -> str:
    """Build a hierarchical slug: {pref}/{city}/{facility-name}.

    Example: tokyo/suginami/tac-kamiigusa-sports-center
    """
    try:
        return build_hierarchical_slug(name=name, pref=pref, city=city)
    except ValueError as e:
        raise CandidateServiceError(str(e)) from e


def _extract_center_no(url: str | None) -> int | None:
    if not url:
        return None
    match = _CENTER_NO_PAT.search(url)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:  # pragma: no cover - defensive
        return None


def _to_intro_base_url(url: str | None) -> str | None:
    if not url:
        return None
    match = _INTRO_BASE_PAT.search(url)
    if not match:
        return None
    end = match.end(1)
    return f"{url[:end]}/"


async def _find_gym_by_official_url(session: AsyncSession, url: str) -> Gym | None:
    stmt = select(Gym).where(Gym.official_url == url)
    result = await session.execute(stmt)
    return result.scalars().first()


async def _find_gym_by_center_no_intro(session: AsyncSession, center_no: int) -> Gym | None:
    pattern = f"%/sports_center{center_no}/%"
    stmt = select(Gym).where(Gym.official_url.like(pattern))
    result = await session.execute(stmt)
    for gym in result.scalars():
        official = gym.official_url or ""
        if _extract_center_no(official) != center_no:
            continue
        base = _to_intro_base_url(official)
        if base and official.rstrip("/") == base.rstrip("/"):
            return gym
    return None


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
    category: str | None,
    has_coords: bool | None,
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
    if category:
        conditions.append(GymCandidate.categories.contains([category.strip()]))
    if has_coords is True:
        conditions.append(GymCandidate.latitude.isnot(None))
        conditions.append(GymCandidate.longitude.isnot(None))
    elif has_coords is False:
        conditions.append(or_(GymCandidate.latitude.is_(None), GymCandidate.longitude.is_(None)))
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
    category: str | None = None,
    has_coords: bool | None = None,
    limit: int,
    cursor: str | None,
) -> tuple[list[CandidateRow], str | None, int]:
    from sqlalchemy import func

    if limit < 1 or limit > 100:
        raise CandidateServiceError("limit must be between 1 and 100")
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    # Count total matching records (without cursor/pagination)
    count_stmt = await _base_query(session)
    count_stmt = _apply_filters(
        count_stmt,
        status=status,
        source=source,
        q=q,
        pref=pref,
        city=city,
        category=category,
        has_coords=has_coords,
        cursor=None,  # No cursor for count query
    )
    count_result = await session.execute(select(func.count()).select_from(count_stmt.subquery()))
    total_count = count_result.scalar() or 0

    # Fetch paginated results
    stmt = await _base_query(session)
    stmt = _apply_filters(
        stmt,
        status=status,
        source=source,
        q=q,
        pref=pref,
        city=city,
        category=category,
        has_coords=has_coords,
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
    return items, next_cursor, total_count


async def _fetch_candidate_row(session: AsyncSession, candidate_id: int) -> CandidateRow:
    stmt = await _base_query(session)
    stmt = stmt.where(GymCandidate.id == candidate_id)
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise LookupError("candidate not found")
    return CandidateRow(candidate=row[0], page=row[1], source=row[2])


async def create_manual_candidate(
    session: AsyncSession, payload: AdminCandidateCreate
) -> CandidateRow:
    source_stmt = select(Source).where(
        Source.source_type == SourceType.user_submission,
        Source.title == "manual",
        Source.url.is_(None),
    )
    source_result = await session.execute(source_stmt)
    source = source_result.scalars().first()
    if source is None:
        source = Source(source_type=SourceType.user_submission, title="manual", url=None)
        session.add(source)
        await session.flush()

    page_url = payload.official_url or f"manual:submission:{uuid4()}"
    now = datetime.now(UTC)
    page = ScrapedPage(
        source_id=int(source.id),
        url=page_url,
        fetched_at=now,
        http_status=0,
        response_meta={"kind": "manual"},
    )
    session.add(page)
    await session.flush()

    parsed_json = dict(payload.parsed_json) if payload.parsed_json else {}
    if payload.official_url:
        parsed_json.setdefault("official_url", payload.official_url)
    if payload.equipments is not None:
        parsed_json["equipments_assign"] = [
            assign.dict(exclude_none=True) for assign in payload.equipments
        ]
        parsed_json.setdefault(
            "equipments", [assign.slug for assign in payload.equipments if assign.slug]
        )

    candidate = GymCandidate(
        source_page_id=int(page.id),
        name_raw=payload.name_raw,
        address_raw=payload.address_raw,
        pref_slug=payload.pref_slug,
        city_slug=payload.city_slug,
        latitude=payload.latitude,
        longitude=payload.longitude,
        parsed_json=parsed_json or None,
        status=CandidateStatus.new,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return await _fetch_candidate_row(session, int(candidate.id))


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

    # Try to resolve gym_id if possible
    gym_id: int | None = None
    official_url = (candidate.parsed_json or {}).get("official_url")
    if official_url:
        # Find by official URL
        stmt = select(Gym.id).where(Gym.official_url == official_url).limit(1)
        gym_id = await session.scalar(stmt)

    if gym_id is None and similar:
        # If no official URL match, but we have similar gyms,
        # checking if we definitely know which one it is difficult without explicit link.
        # But if the candidate is APPROVED, we might want to try harder to find the gym.
        # For now, we only use official_url exact match.
        pass

    return CandidateDetailRow(
        candidate=row.candidate,
        page=row.page,
        source=row.source,
        similar=similar,
        gym_id=gym_id,
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
        canonical_id=gym.canonical_id,
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
    canonical_id: str,
    pref_slug: str,
    city_slug: str,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    parsed_json: dict[str, Any] | None = None,
    official_url: str | None = None,
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
        canonical_id=canonical_id,
        pref_slug=pref_slug,
        city_slug=city_slug,
        address=address,
        latitude=lat,
        longitude=lon,
        parsed_json=parsed_json,
    )


async def _apply_gym_upsert(
    session: AsyncSession,
    existing: Gym | None,
    *,
    slug: str,
    name: str,
    canonical_id: str,
    pref_slug: str,
    city_slug: str,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    parsed_json: dict[str, Any] | None = None,
    official_url: str | None = None,
) -> Gym:
    if existing is None:
        gym = Gym(
            slug=slug,
            name=name,
            canonical_id=canonical_id,
            pref=pref_slug,
            city=city_slug,
            address=address,
            latitude=latitude,
            longitude=longitude,
            parsed_json=parsed_json,
            official_url=official_url,
        )
        session.add(gym)
        await session.flush()
        return gym
    gym = existing
    gym.slug = slug  # Update slug to new hierarchical format
    gym.name = name
    gym.canonical_id = canonical_id
    gym.pref = pref_slug
    gym.city = city_slug
    gym.address = address
    if gym.latitude is None and latitude is not None:
        gym.latitude = latitude
    if gym.longitude is None and longitude is not None:
        gym.longitude = longitude
    if parsed_json is not None:
        gym.parsed_json = parsed_json
    if official_url is not None:
        gym.official_url = official_url
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
    page_url = getattr(row.page, "url", "") or ""
    is_article = bool(_ARTICLE_PAT.search(page_url))
    intro_url = _to_intro_base_url(page_url) if is_article else None
    center_no = _extract_center_no(page_url)
    candidate_name = _sanitize_text(candidate.name_raw)
    candidate_pref = _sanitize_text(candidate.pref_slug)
    candidate_city = _sanitize_text(candidate.city_slug)
    candidate_address = _sanitize_text(candidate.address_raw)
    override_name = _sanitize_text(override.name)
    override_pref = _sanitize_text(override.pref_slug)
    override_city = _sanitize_text(override.city_slug)
    override_address = _sanitize_text(override.address)
    name = override_name or candidate_name
    pref_slug = override_pref or candidate_pref
    city_slug = override_city or candidate_city
    address = override_address or candidate_address
    latitude = override.latitude if override.latitude is not None else candidate.latitude
    longitude = override.longitude if override.longitude is not None else candidate.longitude
    official_url = override.official_url or (
        candidate.parsed_json.get("official_url") if candidate.parsed_json else None
    )
    if not name:
        raise CandidateServiceError("name is required")
    if not pref_slug:
        raise CandidateServiceError("pref_slug is required")
    if not city_slug:
        raise CandidateServiceError("city_slug is required")
    assigns = _collect_equipment_assigns(request.equipments, candidate.parsed_json)
    target_gym: Gym | None = None
    if intro_url:
        target_gym = await _find_gym_by_official_url(session, intro_url)
    if target_gym is None and center_no is not None:
        target_gym = await _find_gym_by_center_no_intro(session, center_no)
    if target_gym:
        preview_summary, preview_latest = await ensure_equipment_links(
            session,
            target_gym,
            assigns,
            apply_changes=False,
        )
        if request.dry_run:
            return ApprovePreview(
                preview=ApproveSummary(
                    gym=_gym_to_preview(target_gym),
                    equipments=preview_summary,
                )
            )
        summary, latest = await ensure_equipment_links(
            session,
            target_gym,
            assigns,
            apply_changes=True,
        )
        latest_cached = _as_naive_utc(latest)
        preview_cached = _as_naive_utc(preview_latest)
        if latest_cached:
            target_gym.last_verified_at_cached = latest_cached
        elif preview_cached:
            target_gym.last_verified_at_cached = preview_cached
        candidate.status = CandidateStatus.approved
        await session.flush()
        await session.commit()
        return ApproveResult(
            result=ApproveSummary(
                gym=_gym_to_preview(target_gym),
                equipments=summary,
            )
        )
    if is_article and (not address or not pref_slug or not city_slug or _is_generic_title(name)):
        raise CandidateServiceError("cannot create gym from article page")
    slug = _build_slug(name, address, city_slug, pref_slug)
    canonical_id = make_canonical_id(pref_slug, city_slug, name)
    canonical_stmt = select(Gym).where(Gym.canonical_id == canonical_id)
    existing_result = await session.execute(canonical_stmt)
    existing_gym = existing_result.scalars().first()
    if existing_gym is None:
        existing_stmt = select(Gym).where(Gym.slug == slug)
        existing_result = await session.execute(existing_stmt)
        existing_gym = existing_result.scalars().first()
    preview_gym = _compose_gym_preview(
        existing_gym,
        slug=slug,
        name=name,
        canonical_id=canonical_id,
        pref_slug=pref_slug,
        city_slug=city_slug,
        address=address,
        latitude=latitude,
        longitude=longitude,
        parsed_json=candidate.parsed_json,
        official_url=official_url,
    )
    preview_summary, preview_latest = await ensure_equipment_links(
        session,
        existing_gym,
        assigns,
        apply_changes=False,
    )
    if request.dry_run:
        return ApprovePreview(preview=ApproveSummary(gym=preview_gym, equipments=preview_summary))

    # Try to scrape official URL if different from scraped page
    scraped_page_url = getattr(row.page, "url", None) if row.page else None
    merged_parsed_json = await try_scrape_official_url(
        official_url,
        scraped_page_url,
        candidate.parsed_json,
    )
    final_parsed_json = merged_parsed_json or candidate.parsed_json
    try:
        gym = await _apply_gym_upsert(
            session,
            existing_gym,
            slug=slug,
            name=name,
            canonical_id=canonical_id,
            pref_slug=pref_slug,
            city_slug=city_slug,
            address=address,
            latitude=preview_gym.latitude,
            longitude=preview_gym.longitude,
            parsed_json=final_parsed_json,
            official_url=official_url,
        )
        await set_current_slug(session, gym, slug)
        page_url = getattr(row.page, "url", None)
        source_url = getattr(row.source, "url", None) if row.source else None
        official = page_url or source_url
        if official and existing_gym is None and not gym.official_url:
            gym.official_url = official
        elif official and not getattr(gym, "official_url", None):
            gym.official_url = official
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


@dataclass
class IngestResult:
    """Result of ingesting a single URL."""

    url: str
    success: bool
    candidate_id: int | None = None
    facility_name: str | None = None
    error: str | None = None


@dataclass
class ExtractedFacility:
    """Extracted facility information from HTML."""

    name: str
    address: str | None = None
    phone: str | None = None
    extra: dict[str, object] | None = None


def _extract_facilities_from_html(html: str) -> list[ExtractedFacility]:
    """Extract multiple facilities from HTML table structure.

    This function parses HTML looking for table structures that contain
    facility listings (common in Japanese government websites).
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    facilities: list[ExtractedFacility] = []

    # Common patterns for facility listing tables
    # Pattern 1: Look for tables with facility-like rows
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Check if this looks like a facility listing table
        # by examining the first row (header) or content patterns
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            # Get text from first cell - potential facility name
            first_cell_text = cells[0].get_text(strip=True)
            if not first_cell_text:
                continue

            # Skip header rows (common header keywords)
            header_keywords = ["施設名", "名称", "場所", "コート", "種別", "設備"]
            if any(kw in first_cell_text for kw in header_keywords) and len(cells) > 1:
                # Could be a header row, skip
                second_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                if any(kw in second_cell for kw in ["所在地", "住所", "電話", "種別"]):
                    continue

            # Look for facility name patterns
            # Japanese facility names often end with 公園, 体育館, センター, etc.
            facility_keywords = [
                "公園",
                "体育館",
                "センター",
                "プール",
                "コート",
                "広場",
                "グラウンド",
                "野球場",
                "テニス",
                "スポーツ",
                "運動",
                "スタジアム",
                "アリーナ",
            ]

            # Check if first cell contains a facility name
            is_facility_name = any(kw in first_cell_text for kw in facility_keywords)

            # Also check if it starts with Japanese characters (likely a name)
            has_japanese = bool(
                re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", first_cell_text)
            )

            if is_facility_name or (has_japanese and len(first_cell_text) < 50):
                # Extract facility name (may include phone number)
                name = first_cell_text
                phone = None
                address = None

                # Try to extract phone number from name if present
                phone_match = re.search(r"[（(]?([\d\-－]+)[）)]?$", name)
                if phone_match:
                    phone = phone_match.group(1).replace("－", "-")
                    name = re.sub(r"[（(]?[\d\-－]+[）)]?$", "", name).strip()

                # Look for address in other cells
                for cell in cells[1:]:
                    cell_text = cell.get_text(strip=True)
                    # Address patterns (contains 区, 市, 町, 丁目, etc.)
                    if re.search(r"[都道府県市区町村]|丁目|番地|号", cell_text):
                        address = cell_text
                        break
                    # Phone pattern in separate cell
                    if not phone and re.search(r"^[\d\-－]+$", cell_text):
                        phone = cell_text.replace("－", "-")

                # Skip if name is too short or looks like a number
                if len(name) >= 2 and not name.isdigit():
                    # Skip non-facility names (common administrative terms)
                    skip_keywords = [
                        "受付",
                        "窓口",
                        "時間",
                        "料金",
                        "注意",
                        "申込",
                        "利用",
                        "ご案内",
                        "お知らせ",
                        "備考",
                        "その他",
                        "休場",
                        "開設",
                    ]
                    if any(kw in name for kw in skip_keywords):
                        continue

                    facilities.append(
                        ExtractedFacility(
                            name=name,
                            address=address,
                            phone=phone,
                        )
                    )

    # Deduplicate by name
    seen_names: set[str] = set()
    unique_facilities: list[ExtractedFacility] = []
    for f in facilities:
        if f.name not in seen_names:
            seen_names.add(f.name)
            unique_facilities.append(f)

    return unique_facilities


def _extract_title_from_html(html: str) -> str | None:
    """Extract the page title from HTML."""

    # Try to find <title> tag
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        # Clean up common suffixes
        for suffix in [" - ", " | ", " – ", "｜"]:
            if suffix in title:
                title = title.split(suffix)[0].strip()
        return title if title else None

    # Try to find <h1> tag
    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    if h1_match:
        return h1_match.group(1).strip() or None

    return None


async def ingest_urls(
    session: AsyncSession,
    urls: list[str],
    pref_slug: str,
    city_slug: str,
    *,
    dry_run: bool = False,
) -> list[IngestResult]:
    """Ingest URLs and create candidates from them.

    For each URL:
    1. Fetch the URL
    2. Try to extract multiple facilities from HTML tables
    3. If multiple facilities found, create a candidate for each
    4. If no facilities found, fall back to page title

    This is useful for pages that list multiple facilities in a table,
    such as Japanese government websites listing sports facilities.

    Args:
        session: Database session
        urls: List of URLs to ingest
        pref_slug: Prefecture slug for all candidates
        city_slug: City slug for all candidates
        dry_run: If True, don't commit to database

    Returns:
        List of IngestResult objects with status for each URL/facility
    """
    from app.services.http_utils import fetch_url_checked

    # Get or create the "url_ingest" source
    source_stmt = select(Source).where(
        Source.source_type == SourceType.user_submission,
        Source.title == "url_ingest",
    )
    source_result = await session.execute(source_stmt)
    source = source_result.scalars().first()
    if source is None:
        source = Source(source_type=SourceType.user_submission, title="url_ingest", url=None)
        session.add(source)
        await session.flush()

    results: list[IngestResult] = []

    for url in urls:
        try:
            # Fetch the URL
            html, status_code, failure_reason = await fetch_url_checked(url)
            if html is None or failure_reason:
                results.append(
                    IngestResult(
                        url=url,
                        success=False,
                        error=failure_reason or "Failed to fetch URL",
                    )
                )
                continue

            # Try to extract multiple facilities from HTML tables
            facilities = _extract_facilities_from_html(html)

            # If no facilities found, fall back to page title
            if not facilities:
                facility_name = _extract_title_from_html(html)
                if not facility_name:
                    # Use URL path as fallback
                    from urllib.parse import urlparse

                    path = urlparse(url).path
                    facility_name = path.split("/")[-1] or path.split("/")[-2] or "Unknown"
                    facility_name = facility_name.replace("-", " ").replace("_", " ").title()
                facilities = [ExtractedFacility(name=facility_name)]

            # Create ScrapedPage (shared by all facilities from this URL)
            now = datetime.now(UTC)
            page = ScrapedPage(
                source_id=int(source.id),
                url=url,
                fetched_at=now,
                http_status=status_code or 200,
                response_meta={"kind": "url_ingest", "facility_count": len(facilities)},
            )
            if not dry_run:
                session.add(page)
                await session.flush()

            # Create a candidate for each facility
            for facility in facilities:
                if dry_run:
                    results.append(
                        IngestResult(
                            url=url,
                            success=True,
                            candidate_id=None,
                            facility_name=facility.name,
                        )
                    )
                    continue

                # Prepare parsed_json
                parsed_json: dict[str, object] = {
                    "source_url": url,
                    "facility_name": facility.name,
                }
                if facility.phone:
                    parsed_json["phone"] = facility.phone

                # Create GymCandidate
                candidate = GymCandidate(
                    source_page_id=int(page.id),
                    name_raw=str(facility.name),
                    address_raw=facility.address,
                    pref_slug=pref_slug,
                    city_slug=city_slug,
                    latitude=None,
                    longitude=None,
                    parsed_json=parsed_json,
                    status=CandidateStatus.new,
                )
                session.add(candidate)
                await session.flush()

                results.append(
                    IngestResult(
                        url=url,
                        success=True,
                        candidate_id=int(candidate.id),
                        facility_name=facility.name,
                    )
                )

        except Exception as exc:
            results.append(
                IngestResult(
                    url=url,
                    success=False,
                    error=str(exc),
                )
            )

    if not dry_run:
        await session.commit()
    else:
        await session.rollback()

    return results
