from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_suggest_service
from app.schemas.common import ErrorResponse
from app.schemas.suggest import GymSuggestItem
from app.services.suggest import SuggestService

router = APIRouter(prefix="/suggest", tags=["suggest"])


@router.get(
    "/equipments",
    response_model=list[str],
    summary="設備名サジェスト（部分一致）",
    description="equipments.name を ILIKE 部分一致で検索し、名前配列を返します。",
    responses={503: {"model": ErrorResponse, "description": "database unavailable"}},
)
async def suggest_equipments(
    q: str = Query(..., description="部分一致（ILIKE）"),
    limit: int = Query(5, ge=1, le=100),
    svc: SuggestService = Depends(get_suggest_service),
):
    return await svc.suggest_equipment_names(q, limit)


@router.get(
    "/gyms",
    response_model=list[GymSuggestItem],
    summary="ジム名/地名サジェスト（部分一致）",
    description=(
        "gyms.name と gyms.city を ILIKE 部分一致で検索し、{slug,name,pref,city} の配列を返します。"
    ),
    responses={503: {"model": ErrorResponse, "description": "database unavailable"}},
)
async def suggest_gyms(
    q: str = Query(..., description="部分一致（ILIKE）"),
    pref: str | None = Query(None, description="都道府県スラッグ（任意）"),
    limit: int = Query(10, ge=1, le=100),
    svc: SuggestService = Depends(get_suggest_service),
):
    return await svc.suggest_gyms(q, pref, limit)
