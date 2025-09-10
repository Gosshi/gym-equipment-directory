from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.deps import get_db
from app.services.gym_detail import (
    get_gym_detail as svc_get_gym_detail,
)
from app.services.gym_search import search_gyms as svc_search_gyms_service
from app.utils.datetime import dt_to_token

router = APIRouter(prefix="/gyms", tags=["gyms"])


@router.get(
    "/search",
    response_model=schemas.GymSearchResponse,
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
    equipment_match: str = Query("any", description="any or all match for equipments filter"),
    sort: str = Query("freshness"),
    page_token: str | None = Query(
        None,
        examples=["v1:freshness:nf=0,ts=1725555555,id=42"],
        description="Keysetの継続トークン。sortと整合しない値は400を返す。",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if equipment_match not in ("any", "all"):
        raise HTTPException(status_code=400, detail="invalid equipment_match")
    # CSV を list[str] に
    equip_list = [s.strip() for s in equipments.split(",")] if equipments else None

    # service へ移譲（既存挙動を丸ごと再現）
    try:
        result = await svc_search_gyms_service(
            db,
            pref=pref,
            city=city,
            equipments=equip_list,
            equipment_match=equipment_match,
            sort=sort,
            page_token=page_token,
            page=page,
            per_page=per_page,
        )
    except ValueError:
        # 無効な page_token など
        raise HTTPException(status_code=400, detail="invalid page_token")

    # last_verified_at をトークン化して schemas へ
    items = []
    for it in result["items"]:
        new = dict(it)
        new["last_verified_at"] = dt_to_token(it.get("last_verified_at"))
        items.append(schemas.GymSummary.model_validate(new))

    return schemas.GymSearchResponse(
        items=items,
        total=result["total"],
        has_next=result["has_next"],
        page_token=result["page_token"],
    )


@router.get("/{slug}", response_model=schemas.GymDetailResponse)
async def get_gym_detail(
    slug: str, include: str | None = Query(None), db: AsyncSession = Depends(get_db)
):
    detail = await svc_get_gym_detail(db, slug, include_score=(include == "score"))
    if detail is None:
        raise HTTPException(status_code=404, detail="gym not found")

    # convert updated_at (datetime) into token
    updated_at_token = dt_to_token(detail.get("updated_at")) if detail.get("updated_at") else None

    return schemas.GymDetailResponse(
        id=detail["id"],
        slug=detail["slug"],
        name=detail["name"],
        city=detail["city"],
        pref=detail["pref"],
        equipments=detail["equipments"],
        updated_at=updated_at_token,
        freshness=detail.get("freshness"),
        richness=detail.get("richness"),
        score=detail.get("score"),
    )
