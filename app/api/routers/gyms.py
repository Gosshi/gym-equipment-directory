# app/api/routers/gyms.py
from typing import Literal, Optional, List

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
        "`sort=richness` は設備充実度スコアの高い順。"
    ),
)
async def search_gyms(
    request: Request,
    pref: Optional[str] = Query(None, description="都道府県スラッグ", examples={"ex": {"value": "chiba"}}),
    city: Optional[str] = Query(None, description="市区町村スラッグ", examples={"ex": {"value": "funabashi"}}),
    equipments: Optional[str] = Query(None, description="CSV: squat-rack,dumbbell", examples={"ex": {"value": "squat-rack,dumbbell"}}),
    equipment_match: Literal["all", "any"] = Query("all", description="設備一致条件（all|any）"),
    sort: Literal["freshness", "richness"] = Query("freshness", description="並び替え（freshness|richness）"),
    page: int = Query(1, ge=1, le=50, description="ページ番号（1始まり）"),
    per_page: int = Query(20, ge=1, le=50, description="1ページ件数（最大50）"),
    session: AsyncSession = Depends(get_async_session),
):
    # 1) 設備スラッグの取得
    required_slugs: List[str] = get_equipment_slugs_from_query(request)
    if equipments and not required_slugs:
        required_slugs = [s.strip() for s in equipments.split(",") if s.strip()]

    # 2) ベース: Gym.id（pref/city を反映）
    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(func.lower(Gym.prefecture) == func.lower(pref))
    if city:
        base_ids = base_ids.where(func.lower(Gym.city) == func.lower(city))

    # 3) 設備フィルタ（all/any）
    if required_slugs:
        eq_ids_stmt = select(Equipment.id).where(Equipment.slug.in_(required_slugs))

        if equipment_match == "any":
            base_ids = (
                select(Gym.id)
                .join(GymEquipment, GymEquipment.gym_id == Gym.id)
                .where(GymEquipment.equipment_id.in_(eq_ids_stmt))
                .where(Gym.id.in_(base_ids))
                .distinct()
            )
        else:  # all
            ge_grouped_stmt = (
                select(GymEquipment.gym_id)
                .where(GymEquipment.equipment_id.in_(eq_ids_stmt))
                .group_by(GymEquipment.gym_id)
                .having(func.count(func.distinct(GymEquipment.equipment_id)) == len(required_slugs))
            )
            base_ids = (
                select(Gym.id)
                .where(Gym.id.in_(ge_grouped_stmt))
                .where(Gym.id.in_(base_ids))
            )

    # 4) total
    total = (await session.scalar(select(func.count()).select_from(base_ids.subquery()))) or 0
    if total == 0:
        return GymSearchResponse(items=[], page=page, per_page=per_page, total=0, has_next=False)

    offset = (page - 1) * per_page

    # 5) 並びと取得
    if sort == "freshness":
        # last_verified_at_cached DESC NULLS LAST, id ASC
        gyms_stmt = (
            select(Gym)
            .where(Gym.id.in_(base_ids.subquery()))
            .order_by(Gym.last_verified_at_cached.desc().nulls_last(), Gym.id.asc())
            .limit(per_page)
            .offset(offset)
        )
        gyms = (await session.scalars(gyms_stmt)).all()

    else:  # richness
        # 各設備行のスコア：1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1)*0.1
        score_expr = (
            1.0
            + func.least(func.coalesce(GymEquipment.count, 0), 5) * 0.1
            + func.least(func.coalesce(GymEquipment.max_weight_kg, 0) / 60.0, 1.0) * 0.1
        )
        score_subq = (
            select(
                GymEquipment.gym_id.label("gym_id"),
                func.sum(score_expr).label("score"),
            )
            .select_from(GymEquipment)
            .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        )
        if required_slugs:
            score_subq = score_subq.where(Equipment.slug.in_(required_slugs))
        score_subq = score_subq.group_by(GymEquipment.gym_id).subquery()

        gyms_stmt = (
            select(Gym)
            .join(score_subq, score_subq.c.gym_id == Gym.id, isouter=True)
            .where(Gym.id.in_(base_ids.subquery()))
            .order_by(score_subq.c.score.desc().nulls_last(), Gym.id.asc())
            .limit(per_page)
            .offset(offset)
        )
        gyms = (await session.scalars(gyms_stmt)).all()

    # 6) 整形
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


# app/api/routers/gyms.py の get_gym_detail を置き換え
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

    rows = (await session.execute(
        select(
            Equipment.slug.label("equipment_slug"),
            Equipment.name.label("equipment_name"),
            Equipment.category,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
            GymEquipment.last_verified_at,
        )
        .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.category, Equipment.name)
    )).all()

    equipments = [
        {
            "equipment_slug": r.equipment_slug,
            "equipment_name": r.equipment_name,
            "category": r.category,
            "count": r.count,
            "max_weight_kg": r.max_weight_kg,
            "verification_status": "verified",  # フィールド必須なら暫定値（実データに合わせて後で拡張）
            "last_verified_at": r.last_verified_at,
        }
        for r in rows
    ]
    updated_at = max((r.last_verified_at for r in rows if r.last_verified_at), default=None)

    return {
        "gym": {
            "id": gym.id,
            "name": gym.name,
            "slug": gym.slug,
            "prefecture": gym.prefecture,
            "city": gym.city,
        },
        "equipments": equipments,
        "sources": [],
        "updated_at": updated_at,
    }
