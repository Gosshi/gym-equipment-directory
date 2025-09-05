from typing import Optional, List
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Equipment
from app.schemas.common import ErrorResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/equipments")


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
    q: Annotated[
        Optional[str],
        Query(
            description="部分一致キーワード（未指定なら全件上限20件）",
            examples={
                "by-name": {"value": "スクワット"},
                "by-slug": {"value": "dumb"},
            },
        ),
    ] = None,
    session: AsyncSession = Depends(get_async_session),
) -> List[EquipmentMaster]:
    stmt = select(Equipment.id, Equipment.slug, Equipment.name, Equipment.category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Equipment.name.ilike(like), Equipment.slug.ilike(like)))
    stmt = stmt.order_by(func.lower(Equipment.slug)).limit(20)
    rows = (await session.execute(stmt)).all()
    return [EquipmentMaster.model_validate(dict(r._mapping)) for r in rows]
