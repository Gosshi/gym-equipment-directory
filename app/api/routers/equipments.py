from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_equipment_service
from app.schemas.common import ErrorResponse
from app.services.equipments import EquipmentService

router = APIRouter(prefix="/equipments", tags=["equipments"])


class EquipmentMaster(BaseModel):
    id: int = Field(description="設備ID")
    slug: str = Field(description="スラッグ（lower-case, kebab）")
    name: str = Field(description="表示名")
    category: str | None = Field(None, description="カテゴリ（任意）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 12,
                "slug": "squat-rack",
                "name": "スクワットラック",
                "category": "free-weights",
            }
        }
    }


@router.get(
    "",
    response_model=list[EquipmentMaster],
    responses={404: {"model": ErrorResponse}},
    summary="設備マスタ検索（補完用）",
    description="設備マスタを name/slug の部分一致で検索します（最大20件）。",
)
async def list_equipments(
    q: str | None = Query(None, description="部分一致（ILIKE風）"),
    limit: int = Query(20, ge=1, le=100),
    svc: EquipmentService = Depends(get_equipment_service),
):
    result = await svc.list(q, limit)
    return [m.model_dump() for m in result]
