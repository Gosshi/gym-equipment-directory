from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.deps import get_db
from app.services.gym_search import search_gyms as svc_search_gyms_service
from app.services.gym_detail import (
    get_gym_detail_v1 as svc_get_gym_detail,
)

router = APIRouter(prefix="/gyms", tags=["gyms"])



@router.get(
    "/search",
    response_model=schemas.SearchResponse,
    responses={
        400: {
            "description": "Invalid page_token",
            "content": {"application/json": {"example": {"detail": "invalid page_token"}}},
        }
    },
)
async def search_gyms(
    pref: str | None = Query(None, description="都道府県スラッグ（例: chiba）"),
    city: str | None = Query(None, description="市区町村スラッグ（例: funabashi）"),
    equipments: str | None = Query(None, description="CSV: squat-rack,dumbbell"),
    sort: str = Query("freshness", pattern="^(richness|freshness)$"),
    page_token: str | None = Query(
        None,
        example="v1:freshness:nf=0,ts=1725555555,id=42",
        description="Keysetの継続トークン。sortと整合しない値は400を返す。",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    # CSV -> list[str]
    equip_list: list[str] | None = None
    if equipments:
        equip_list = [s.strip() for s in equipments.split(",") if s.strip()]

    # service に委譲（routerは入出力整形のみ）
    try:
        result = await svc_search_gyms_service(
            db,
            pref=pref,
            city=city,
            equipments=equip_list,
            equipment_match="any",  # 既定は any
            sort=sort,
            page_token=page_token,
            page=page,
            per_page=per_page,
        )
    except ValueError:
        # 無効な page_token など
        raise HTTPException(status_code=400, detail="invalid page_token")

    # service -> schemas へ詰め替え
    items: list[schemas.SearchItem] = []
    for it in result["items"]:
        items.append(
            schemas.SearchItem(
                gym=schemas.GymBasic.model_validate(
                    {
                        "id": it.get("id"),
                        "slug": it.get("slug"),
                        "name": it.get("name"),
                        "pref": it.get("pref"),
                        "city": it.get("city"),
                    }
                ),
                highlights=[],  # 必要なら後段で拡張
                last_verified_at=it.get("last_verified_at"),
                score=float(it.get("score", 0.0)),
            )
        )

    return schemas.SearchResponse(items=items, page=page, per_page=per_page, total=result["total"])


@router.get("/{slug}", response_model=schemas.GymDetailResponse)
async def get_gym_detail(slug: str, db: AsyncSession = Depends(get_db)):
    detail = await svc_get_gym_detail(db, slug)
    if detail is None:
        # service 層で見つからなかった場合は 404 を返す
        raise HTTPException(status_code=404, detail="gym not found")
    return detail
