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
    BulkScrapeJobStatus,
    BulkScrapeRequest,
    IngestUrlItem,
    IngestUrlsRequest,
    IngestUrlsResponse,
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
        categories=candidate.categories or [],
        parsed_json=candidate.parsed_json,
        source=_to_source_ref(row),
        fetched_at=row.page.fetched_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        official_url=(candidate.parsed_json or {}).get("official_url"),
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


def _to_bulk_scrape_status(payload: dict[str, object]) -> BulkScrapeJobStatus:
    return BulkScrapeJobStatus(**payload)


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
        rows, next_cursor, total_count = await candidate_service.list_candidates(
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
    return AdminCandidateListResponse(items=items, next_cursor=next_cursor, count=total_count)


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


class ScrapeRequest(BaseModel):
    official_url: str | None = None
    dry_run: bool = False
    scrape_subpages: bool = False  # If True, detect and scrape facility subpages (max 20)


@router.post("/{candidate_id}/scrape", response_model=AdminCandidateItem)
async def scrape_official_url(
    candidate_id: int,
    payload: ScrapeRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    from app.services.scrape_utils import try_scrape_official_url

    candidate = await session.get(candidate_service.GymCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")

    target_url = None
    if payload and payload.official_url:
        target_url = payload.official_url
    else:
        target_url = (candidate.parsed_json or {}).get("official_url")

    if not target_url:
        raise HTTPException(
            status_code=400, detail="No official_url provided or found in candidate"
        )

    # Pass None as existing_page_url since we want to force check even if it matches source
    # (or maybe we pass source page url if available)
    # The requirement is to allow manual scrape.
    parsed_json = candidate.parsed_json or {}

    merged_data = await try_scrape_official_url(
        target_url,
        scraped_page_url=None,  # Force scrape even if it matches something (user action)
        existing_parsed_json=parsed_json,
        scrape_subpages=payload.scrape_subpages if payload else False,
    )

    if merged_data:
        # Update parsed_json for the return object
        # If dry_run is True, we DON'T commit to DB, but we return the modified object
        # so the frontend can see the result.
        candidate.parsed_json = merged_data

        if not (payload and payload.dry_run):
            session.add(candidate)
            await session.commit()
            # Reuse logic below to fetch full details

    # Re-fetch full row
    updated_row = await candidate_service.get_candidate_detail(session, candidate_id)

    # If dry_run, we need to manually inject the preview parsed_json into the result
    # because updated_row will come from DB (which is unchanged).
    if payload and payload.dry_run and merged_data:
        # We need to construct a robust return object.
        # Since updated_row is a dataclass/object, we can't easily mutate it
        # if it's fetched freshly.
        # But we need to return AdminCandidateItem.
        item = _to_item(updated_row)
        item.parsed_json = merged_data
        item.official_url = str(merged_data.get("official_url") or "")
        # Return mapped item directly
        return item  # type: ignore[return-value]

    return _to_item(updated_row)


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


@router.post("/scrape-bulk", response_model=BulkScrapeJobStatus, status_code=202)
async def bulk_scrape_candidates(payload: BulkScrapeRequest):
    from app.services.scrape_queue import enqueue_scrape_job, serialize_job

    job = await enqueue_scrape_job(payload.candidate_ids, dry_run=payload.dry_run)
    return _to_bulk_scrape_status(serialize_job(job))


@router.get("/scrape-bulk/{job_id}", response_model=BulkScrapeJobStatus)
async def get_bulk_scrape_status(job_id: str):
    from app.services.scrape_queue import get_scrape_job, serialize_job

    job = await get_scrape_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="scrape job not found")
    return _to_bulk_scrape_status(serialize_job(job))


@router.post("/ingest-urls", response_model=IngestUrlsResponse)
async def ingest_urls(
    payload: IngestUrlsRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Ingest multiple URLs and create candidates from them.

    Fetches each URL, extracts the page title as facility name,
    and creates a candidate. The user should edit the candidate
    details after creation.
    """
    results = await candidate_service.ingest_urls(
        session,
        payload.urls,
        payload.pref_slug,
        payload.city_slug,
        dry_run=payload.dry_run,
    )

    items = [
        IngestUrlItem(
            url=r.url,
            status="success" if r.success else "failed",
            candidate_id=r.candidate_id,
            facility_name=r.facility_name,
            error=r.error,
        )
        for r in results
    ]

    success_count = sum(1 for r in results if r.success)
    failure_count = len(results) - success_count

    return IngestUrlsResponse(
        items=items,
        success_count=success_count,
        failure_count=failure_count,
        dry_run=payload.dry_run,
    )
