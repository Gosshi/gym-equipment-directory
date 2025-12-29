from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.models.audit_log import AuditLog
from app.models.gym_candidate import CandidateStatus
from app.schemas.admin_candidates import (
    AdminApproveResponse,
    AdminCandidateCreate,
    AdminCandidateDetail,
    AdminCandidateItem,
    AdminCandidateListResponse,
    AdminCandidatePatch,
    AdminSourceRef,
    ApprovePreview,
    ApproveRequest,
    ApproveResult,
    BulkApproveItem,
    BulkApproveRequest,
    BulkApproveResult,
    BulkRejectItem,
    BulkRejectRequest,
    BulkRejectResult,
    RejectRequest,
    ScrapedPageInfo,
    SimilarGymInfo,
)
from app.services import candidates as candidate_service
from app.services.approve_service import (
    ApprovalError,
    ApproveService,
    CandidateNotFoundError,
    CandidateStatusConflictError,
    InvalidCandidatePayloadError,
)
from app.services.candidates import CandidateDetailRow, CandidateRow, CandidateServiceError
from app.services.scrape_utils import try_scrape_official_url


class GeocodeRequest(BaseModel):
    address: str | None = None


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
        category=candidate.category,
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
        gym_id=row.gym_id,
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
    category: str | None = Query(None),
    has_coords: bool | None = Query(None),
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
            category=category,
            has_coords=has_coords,
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


@router.post("/{candidate_id}/geocode", response_model=AdminCandidateItem)
async def geocode_candidate(
    candidate_id: int,
    payload: GeocodeRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    from app.services.geocode import geocode

    candidate = await session.get(candidate_service.GymCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")

    target_address = payload.address if payload and payload.address else candidate.address_raw
    if not target_address:
        raise HTTPException(status_code=400, detail="candidate has no address")

    coords = await geocode(session, target_address)
    if not coords:
        raise HTTPException(status_code=404, detail="geocoding failed")

    candidate.latitude, candidate.longitude = coords
    # If a new address was provided and successfully geocoded, update the candidate's address
    if payload and payload.address:
        candidate.address_raw = payload.address

    await session.commit()

    # Re-fetch full row to return AdminCandidateItem
    updated_row = await candidate_service.get_candidate_detail(session, candidate_id)
    return _to_item(updated_row)


class ScrapeOfficialUrlRequest(BaseModel):
    """Request to scrape an official URL for a candidate."""

    official_url: str


class ScrapeOfficialUrlResponse(BaseModel):
    """Response from scraping an official URL for a candidate."""

    candidate_id: int
    official_url: str
    scraped: bool
    message: str


@router.post("/{candidate_id}/scrape-official-url", response_model=ScrapeOfficialUrlResponse)
async def scrape_candidate_official_url(
    candidate_id: int,
    payload: ScrapeOfficialUrlRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Scrape an official URL for a candidate and merge data into parsed_json.

    This endpoint allows updating the official_url for candidates and triggering
    a scrape to extract additional information. The scraped data is merged
    into the candidate's parsed_json. robots.txt is checked before scraping.
    """
    from sqlalchemy import select

    from app.models.scraped_page import ScrapedPage

    candidate = await session.get(candidate_service.GymCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")

    official_url = payload.official_url.strip()
    if not official_url:
        raise HTTPException(status_code=400, detail="official_url is required")

    # Get the scraped page URL for comparison (from ScrapedPage table)
    scraped_page_url = None
    stmt = select(ScrapedPage.url).where(ScrapedPage.candidate_id == candidate_id).limit(1)
    result = await session.scalar(stmt)
    if result:
        scraped_page_url = result

    # Try to scrape the official URL
    merged_json = await try_scrape_official_url(
        official_url,
        scraped_page_url,
        candidate.parsed_json,
    )

    if merged_json is None:
        # Scraping failed or was skipped, but still update the official_url in parsed_json
        if candidate.parsed_json is None:
            candidate.parsed_json = {}
        elif not isinstance(candidate.parsed_json, dict):
            candidate.parsed_json = {}
        candidate.parsed_json["official_url"] = official_url
        await session.commit()
        return ScrapeOfficialUrlResponse(
            candidate_id=candidate_id,
            official_url=official_url,
            scraped=False,
            message="URL updated but scraping skipped (same URL or robots.txt blocked)",
        )

    # Scraping succeeded, update both parsed_json and official_url
    candidate.parsed_json = merged_json
    await session.commit()

    return ScrapeOfficialUrlResponse(
        candidate_id=candidate_id,
        official_url=official_url,
        scraped=True,
        message="Official URL scraped successfully and merged into candidate data",
    )


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


@router.post("/{candidate_id}/approve-auto", response_model=AdminApproveResponse)
async def approve_candidate_auto(
    candidate_id: int,
    dry_run: bool = Query(False),
    session: AsyncSession = Depends(get_async_session),
):
    service = ApproveService(session)
    try:
        result = await service.approve(candidate_id, dry_run=dry_run)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="candidate not found") from exc
    except CandidateStatusConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidCandidatePayloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()


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


@router.post("/approve-bulk", response_model=BulkApproveResult)
async def bulk_approve_candidates(
    payload: BulkApproveRequest,
    operator: str | None = Query(None, description="Admin operator identifier"),
    session: AsyncSession = Depends(get_async_session),
):
    if not payload.candidate_ids:
        raise HTTPException(status_code=400, detail="candidate_ids required")
    items: list[BulkApproveItem] = []
    success_ids: list[int] = []
    failure_ids: list[int] = []
    service = ApproveService(session)
    for cid in payload.candidate_ids:
        try:
            resp = await service.approve(cid, dry_run=payload.dry_run)
        except CandidateNotFoundError:
            items.append(BulkApproveItem(candidate_id=cid, ok=False, error="not_found"))
            failure_ids.append(cid)
            continue
        except CandidateStatusConflictError:
            items.append(BulkApproveItem(candidate_id=cid, ok=False, error="status_conflict"))
            failure_ids.append(cid)
            continue
        except InvalidCandidatePayloadError:
            items.append(BulkApproveItem(candidate_id=cid, ok=False, error="invalid_payload"))
            failure_ids.append(cid)
            continue
        except ApprovalError as exc:
            items.append(BulkApproveItem(candidate_id=cid, ok=False, error=str(exc)))
            failure_ids.append(cid)
            continue
        items.append(BulkApproveItem(candidate_id=cid, ok=True, payload=resp.to_dict()))
        success_ids.append(cid)

    audit_id: int | None = None
    if not payload.dry_run:
        log = AuditLog(
            action="bulk_approve",
            operator=operator,
            candidate_ids=payload.candidate_ids,
            success_ids=success_ids,
            failure_ids=failure_ids,
            dry_run=False,
        )
        session.add(log)
        await session.flush()
        audit_id = int(log.id)
        await session.commit()
    else:
        await session.rollback()  # 明示的に念のため

    return BulkApproveResult(
        items=items,
        success_count=len(success_ids),
        failure_count=len(failure_ids),
        dry_run=payload.dry_run,
        audit_log_id=audit_id,
    )


@router.post("/reject-bulk", response_model=BulkRejectResult)
async def bulk_reject_candidates(
    payload: BulkRejectRequest,
    operator: str | None = Query(None, description="Admin operator identifier"),
    session: AsyncSession = Depends(get_async_session),
):
    if not payload.candidate_ids:
        raise HTTPException(status_code=400, detail="candidate_ids required")
    if not payload.reason:
        raise HTTPException(status_code=400, detail="reason required")
    items: list[BulkRejectItem] = []
    success_ids: list[int] = []
    failure_ids: list[int] = []
    for cid in payload.candidate_ids:
        if payload.dry_run:
            # Dry-run: 候補存在確認のみ
            candidate = await session.get(candidate_service.GymCandidate, cid)  # type: ignore[attr-defined]
            if not candidate:
                items.append(BulkRejectItem(candidate_id=cid, ok=False, error="not_found"))
                failure_ids.append(cid)
                continue
            items.append(BulkRejectItem(candidate_id=cid, ok=True, status=CandidateStatus.rejected))
            success_ids.append(cid)
            continue
        try:
            row = await candidate_service.reject_candidate(session, cid, payload.reason)
        except LookupError:
            items.append(BulkRejectItem(candidate_id=cid, ok=False, error="not_found"))
            failure_ids.append(cid)
            continue
        items.append(BulkRejectItem(candidate_id=cid, ok=True, status=row.candidate.status))
        success_ids.append(cid)

    audit_id: int | None = None
    if not payload.dry_run:
        log = AuditLog(
            action="bulk_reject",
            operator=operator,
            candidate_ids=payload.candidate_ids,
            success_ids=success_ids,
            failure_ids=failure_ids,
            reason=payload.reason,
            dry_run=False,
        )
        session.add(log)
        await session.flush()
        audit_id = int(log.id)
        await session.commit()
    else:
        await session.rollback()

    return BulkRejectResult(
        items=items,
        success_count=len(success_ids),
        failure_count=len(failure_ids),
        dry_run=payload.dry_run,
        audit_log_id=audit_id,
    )
