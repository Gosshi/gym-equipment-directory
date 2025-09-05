# app/api/routers/gyms.py
from typing import Optional, List, Literal

from app.schemas.common import ErrorResponse
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Gym, Equipment, GymEquipment
from app.schemas.gym_search import GymSummary, GymSearchResponse
from app.schemas.gym_detail import GymDetailResponse
from app.schemas.common import ErrorResponse
from app.api.deps import get_equipment_slugs_from_query

router = APIRouter(prefix="/gyms", tags=["gyms"])


@router.get(
    "/search",
    response_model=GymSearchResponse,
    summary="ジム検索（設備フィルタ + ページング）",
    description=(
        "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
        "`sort=freshness` は last_verified_at_cached の新しい順、"
        "`sort=richness` は設備充実度スコアの高い順（※現状は freshness のみ最適化）。"
    ),
)
async def search_gyms(
    request: Request,
    pref: Optional[str] = Query(None, description="都道府県スラッグ", examples={"ex": {"value": "chiba"}}),
    city: Optional[str] = Query(None, description="市区町村スラッグ", examples={"ex": {"value": "funabashi"}}),
    equipments: Optional[str] = Query(None, description="CSV: squat-rack,dumbbell", examples={"ex": {"value": "squat-rack,dumbbell"}}),
    equipment_match: Literal["all","any"] = Query("all", description="設備一致条件（all|any）"),
    sort: Literal["freshness","richness"] = Query("freshness", description="並び替え（freshness|richness）"),
    page: int = Query(1, ge=1, le=50, description="ページ番号（1始まり）"),
    per_page: int = Query(20, ge=1, le=50, description="1ページ件数（最大50）"),
    session: AsyncSession = Depends(get_async_session),
):
    # 1) クエリパラメータから設備スラッグ配列を取得
    #    ※ get_equipment_slugs_from_query は request から 'equipments' を読む想定
    required_slugs: List[str] = get_equipment_slugs_from_query(request)
    if equipments and not required_slugs:
        # 補助: もし deps が未対応なら文字列から直に分解（空白除去）
        required_slugs = [s.strip() for s in equipments.split(",") if s.strip()]

    # 2) ベースとなる Gym.id セレクト（pref/city フィルタ適用）
    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(func.lower(Gym.prefecture) == func.lower(pref))
    if city:
        base_ids = base_ids.where(func.lower(Gym.city) == func.lower(city))

    # 3) 設備フィルタ
    if required_slugs:
        # slug → equipment_id 解決
        eq_ids_subq = select(Equipment.id).where(Equipment.slug.in_(required_slugs)).subquery()

        if equipment_match == "any":
            # どれか一致
            base_ids = (
                select(Gym.id)
                .join(GymEquipment, GymEquipment.gym_id == Gym.id)
                .where(GymEquipment.equipment_id.in_(select(eq_ids_subq)))
                .where(Gym.id.in_(base_ids.subquery()))
                .distinct()
            )
        else:
            # すべて一致 (ALL)
            ge_grouped = (
                select(GymEquipment.gym_id)
                .where(GymEquipment.equipment_id.in_(select(eq_ids_subq)))
                .group_by(GymEquipment.gym_id)
                .having(func.count(func.distinct(GymEquipment.equipment_id)) == len(required_slugs))
            ).subquery()
            base_ids = select(Gym.id).where(Gym.id.in_(select(ge_grouped))).where(Gym.id.in_(base_ids.subquery()))

    # 4) total 件数
    total_stmt = select(func.count()).select_from(base_ids.subquery())
    total = (await session.scalar(total_stmt)) or 0
    if total == 0:
        return GymSearchResponse(items=[], page=page, per_page=per_page, total=0, has_next=False)

    # 5) 並び順: last_verified_at_cached DESC NULLS LAST, id ASC
    order_cols = [
        Gym.last_verified_at_cached.desc().nulls_last(),
        Gym.id.asc(),
    ]

    # 6) 対象ページの ID を取得
    offset = (page - 1) * per_page
    page_ids_stmt = (
        select(Gym.id)
        .where(Gym.id.in_(base_ids.subquery()))
        .order_by(*order_cols)
        .limit(per_page)
        .offset(offset)
    )
    page_ids = [row[0] for row in (await session.execute(page_ids_stmt)).all()]
    if not page_ids:
        return GymSearchResponse(items=[], page=page, per_page=per_page, total=total, has_next=False)

    # 7) 実体取得（同じ並びで）
    gyms_stmt = select(Gym).where(Gym.id.in_(page_ids)).order_by(*order_cols)
    gyms = (await session.scalars(gyms_stmt)).all()

    # 8) 返却整形（要件に合わせて最小）
    items = [
        GymSummary(
            id=g.id,
            name=g.name,
            last_verified_at_cached=g.last_verified_at_cached.isoformat() if g.last_verified_at_cached else None,
        )
        for g in gyms
    ]
    has_next = (page * per_page) < total

    return GymSearchResponse(items=items, page=page, per_page=per_page, total=total, has_next=has_next)

@router.get(
    "/{slug}",
    response_model=GymDetailResponse,
    summary="ジム詳細を取得",
    description="ジムスラッグで詳細情報（設備一覧・最新更新時刻）を返します。",
    responses={404: {"model": ErrorResponse, "description": "ジムが見つかりません"}},
)
async def get_gym_detail(slug: str, session: AsyncSession = Depends(get_async_session)):
    gym = await session.scalar(select(Gym).where(Gym.slug == slug))
    if not gym:
        raise HTTPException(status_code=404, detail="gym not found")