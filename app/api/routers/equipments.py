from typing import Optional, List
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Equipment
from app.schemas.common import ErrorResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/equipments", tags=["equipments"])


class EquipmentMaster(BaseModel):
    id: int = Field(description="設備ID")
    slug: str = Field(description="スラッグ（lower-case, kebab）")
    name: str = Field(description="表示名")
    category: Optional[str] = Field(None, description="カテゴリ（任意）")

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
    response_model=List[EquipmentMaster],
    responses={404: {"model": ErrorResponse}},
    summary="設備マスタ検索（補完用）",
    description="設備マスタを name/slug の部分一致で検索します（最大20件）。",
)
async def list_equipments(
    q: Optional[str] = Query(None, description="部分一致（ILIKE風）"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(Equipment.id, Equipment.slug, Equipment.name, Equipment.category)
    if q:
        ilike = f"%{q}%"
        stmt = stmt.where(or_(Equipment.slug.ilike(ilike), Equipment.name.ilike(ilike)))
    stmt = stmt.order_by(Equipment.slug.asc()).limit(limit)
    rows = await session.execute(stmt)
    return [dict(r) for r in rows.mappings()]
