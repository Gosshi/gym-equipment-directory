from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.schemas.report import ReportAdminListResponse
from app.services.reports import ReportService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/reports", response_model=ReportAdminListResponse, summary="報告一覧（Keyset）")
async def list_reports(
    status: str = Query("open"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    svc = ReportService(session)
    return await svc.admin_list(status=status, limit=limit, cursor_token=cursor)


@router.patch("/reports/{report_id}:resolve", summary="報告を解決済みにする")
async def resolve_report(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    svc = ReportService(session)
    try:
        return await svc.resolve(report_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="report not found")
