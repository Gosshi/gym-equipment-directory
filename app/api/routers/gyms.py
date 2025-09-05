# app/api/routers/gyms.py
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, desc
from sqlalchemy.sql import nulls_last
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Gym, Equipment, GymEquipment
from app.schemas.gym_search import GymSummary, GymSearchResponse
from app.api.deps import get_equipment_slugs_from_query

router = APIRouter(prefix="/gyms", tags=["gyms"])


@router.get(
    "/search",
    response_model=GymSearchResponse,
    summary="ジム検索（設備フィルタ + ページング）",
)
async def search_gyms(
    request: Request,
    equipment_match: Literal["all", "any"] = Query(
        "all", description="設備の合致条件（all: すべて / any: いずれか）"
    ),
    page: int = Query(1, ge=1, description="ページ番号（1始まり）"),
    per_page: int = Query(20, ge=1, le=100, description="1ページ件数（最大100）"),
    session: AsyncSession = Depends(get_async_session),
):
    # クエリパラメータから設備スラッグ配列を取得
    required_slugs = get_equipment_slugs_from_query(request)

    base = select(Gym.id).distinct()

    if required_slugs:
        # slug -> equipment_id 解決
        eq_ids_subq = (
            select(Equipment.id)
            .where(Equipment.slug.in_(required_slugs))
            .subquery()
        )

        if equipment_match == "any":
            # ANY: どれか一致すればOK
            base = (
                select(Gym.id)
                .join(GymEquipment, GymEquipment.gym_id == Gym.id)
                .where(GymEquipment.equipment_id.in_(select(eq_ids_subq)))
                .distinct()
            )
        else:
            # ALL: すべて一致している gym_id のみ
            ge_subq = (
                select(GymEquipment.gym_id)
                .where(GymEquipment.equipment_id.in_(select(eq_ids_subq)))
                .group_by(GymEquipment.gym_id)
                .having(
                    func.count(func.distinct(GymEquipment.equipment_id))
                    == len(required_slugs)
                )
            ).subquery()
            base = select(Gym.id).where(Gym.id.in_(select(ge_subq)))

    # total 件数
    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    # 並び順: last_verified_at_cached DESC NULLS LAST, id ASC
    order_cols = [
        nulls_last(desc(Gym.last_verified_at_cached)),
        Gym.id.asc(),
    ]

    offset = (page - 1) * per_page
    page_ids_stmt = (
        select(Gym.id)
        .where(Gym.id.in_(base))
        .order_by(*order_cols)
        .limit(per_page)
        .offset(offset)
    )
    page_ids = [row[0] for row in (await session.execute(page_ids_stmt)).all()]

    if not page_ids:
        return GymSearchResponse(
            items=[], page=page, per_page=per_page, total=total, has_next=False
        )

    gyms_stmt = (
        select(Gym)
        .where(Gym.id.in_(page_ids))
        .order_by(*order_cols)
    )
    gyms = (await session.execute(gyms_stmt)).scalars().all()

    items = [
        GymSummary(
            id=g.id,
            name=g.name,
            last_verified_at_cached=g.last_verified_at_cached.isoformat()
            if g.last_verified_at_cached
            else None,
        )
        for g in gyms
    ]

    has_next = (page * per_page) < total
    return GymSearchResponse(
        items=items, page=page, per_page=per_page, total=total, has_next=has_next
    )
