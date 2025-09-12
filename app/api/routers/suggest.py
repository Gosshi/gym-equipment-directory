from fastapi import APIRouter, Depends, Query

from app.api.deps import get_suggest_service
from app.schemas.common import ErrorResponse
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
