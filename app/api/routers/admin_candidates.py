from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.models.gym_candidate import CandidateStatus
from app.schemas.admin_candidates import (
    AdminCandidateCreate,
    AdminCandidateDetail,
    AdminCandidateItem,
    AdminCandidateListResponse,
    AdminCandidatePatch,
    AdminSourceRef,
    ApprovePreview,
    ApproveRequest,
    ApproveResult,
    RejectRequest,
    ScrapedPageInfo,
    SimilarGymInfo,
)
from app.services import candidates as candidate_service
from app.services.candidates import CandidateDetailRow, CandidateRow, CandidateServiceError

router = APIRouter(prefix="/admin/candidates", tags=["admin"])


def _to_source_ref(row: CandidateRow) -> AdminSourceRef:
    source = row.source
    source_id = int(source.id) if source and source.id is not None else int(row.page.source_id)
    return AdminSourceRef(
        id=source_id,
        title=getattr(source, "title", None),
        url=getattr(source, "url", None),
    )


def _to_item(row: CandidateRow) -> AdminCandidateItem:
    candidate = row.candidate
    return AdminCandidateItem(
        id=int(candidate.id),
        status=candidate.status,
        name_raw=candidate.name_raw,
        address_raw=candidate.address_raw,
        pref_slug=candidate.pref_slug,
        city_slug=candidate.city_slug,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        parsed_json=candidate.parsed_json,
        source=_to_source_ref(row),
        fetched_at=row.page.fetched_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def _to_detail(row: CandidateDetailRow) -> AdminCandidateDetail:
    item = _to_item(row)
    scraped_page = ScrapedPageInfo(
        url=row.page.url,
        fetched_at=row.page.fetched_at,
        http_status=row.page.http_status,
    )
    similar: list[SimilarGymInfo] | None = None
    if row.similar:
        similar = [
            SimilarGymInfo(gym_id=int(gym.id), gym_slug=gym.slug, gym_name=gym.name)
            for gym in row.similar
        ]
    return AdminCandidateDetail(
        **item.dict(),
        scraped_page=scraped_page,
        similar=similar,
    )


@router.post("", response_model=AdminCandidateItem, status_code=201)
async def create_candidate(
    payload: AdminCandidateCreate, session: AsyncSession = Depends(get_async_session)
):
    try:
        row = await candidate_service.create_manual_candidate(session, payload)
    except CandidateServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_item(row)


@router.get("", response_model=AdminCandidateListResponse)
async def list_candidates(
    status: str | None = Query(None),
    source: str | None = Query(None),
    q: str | None = Query(None),
    pref: str | None = Query(None),
    city: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    status_enum: CandidateStatus | None = None
    if status:
        try:
            status_enum = CandidateStatus(status)
        except ValueError as exc:  # pragma: no cover - FastAPI validation usually catches
            raise HTTPException(status_code=400, detail="invalid status") from exc
    try:
        rows, next_cursor = await candidate_service.list_candidates(
            session,
            status=status_enum,
            source=source,
            q=q,
            pref=pref,
            city=city,
            limit=limit,
            cursor=cursor,
        )
    except CandidateServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = [_to_item(row) for row in rows]
    return AdminCandidateListResponse(items=items, next_cursor=next_cursor, count=len(items))


@router.get("/{candidate_id}", response_model=AdminCandidateDetail)
async def get_candidate_detail(
    candidate_id: int, session: AsyncSession = Depends(get_async_session)
):
    try:
        detail = await candidate_service.get_candidate_detail(session, candidate_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="candidate not found") from exc
    return _to_detail(detail)


@router.patch("/{candidate_id}", response_model=AdminCandidateItem)
async def patch_candidate(
    candidate_id: int,
    payload: AdminCandidatePatch,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        updated = await candidate_service.patch_candidate(session, candidate_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="candidate not found") from exc
    return _to_item(updated)


@router.post(
    "/{candidate_id}/approve",
    response_model=ApprovePreview | ApproveResult,
)
async def approve_candidate(
    candidate_id: int,
    payload: ApproveRequest,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        result = await candidate_service.approve_candidate(session, candidate_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="candidate not found") from exc
    except CandidateServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="gym slug conflict") from exc
    return result


@router.post("/{candidate_id}/reject", response_model=AdminCandidateItem)
async def reject_candidate(
    candidate_id: int,
    payload: RejectRequest,
    session: AsyncSession = Depends(get_async_session),
):
    if not payload.reason:
        raise HTTPException(status_code=400, detail="reason is required")
    try:
        updated = await candidate_service.reject_candidate(session, candidate_id, payload.reason)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="candidate not found") from exc
    return _to_item(updated)
