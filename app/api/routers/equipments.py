from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_equipment_service
from app.dto import EquipmentMasterDTO
from app.schemas.common import ErrorResponse
from app.services.equipments import EquipmentService

router = APIRouter(prefix="/equipments", tags=["equipments"])


@router.get(
    "",
    response_model=list[EquipmentMasterDTO],
    responses={404: {"model": ErrorResponse}},
    summary="設備マスタ検索（補完用）",
    description="設備マスタを name/slug の部分一致で検索します（最大20件）。",
)
async def list_equipments(
    q: str | None = Query(None, description="部分一致（ILIKE風）"),
    limit: int = Query(20, ge=1, le=100),
    svc: EquipmentService = Depends(get_equipment_service),
):
    return await svc.list(q, limit)
