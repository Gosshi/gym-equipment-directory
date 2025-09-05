# app/api/routers/gyms.py
from typing import Literal, Optional, List
from typing_extensions import Annotated
from datetime import datetime
import base64, json

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

def _encode_page_token(k: tuple, sort: str) -> str:
    payload = {"k": list(k), "sort": sort}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _decode_page_token(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())

_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順（1.0  min(count,5)*0.1  min(max_weight_kg/60,1.0)*0.1）\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
)

@router.get(
    "/search",
    response_model=GymSearchResponse,
    summary="ジム検索（設備フィルタ  ページング）",
    description=_DESC,
)
async def search_gyms(
    request: Request,
    pref: Annotated[
        Optional[str],
        Query(
            description="都道府県スラッグ（lower）例: chiba",
            examples={"ex": {"value": "chiba"}},
        ),
    ] = None,
    city: Annotated[
        Optional[str],
        Query(
            description="市区町村スラッグ（lower）例: funabashi",
            examples={"ex": {"value": "funabashi"}},
        ),
    ] = None,
    equipments: Annotated[
        Optional[str],
        Query(
            description="設備スラッグCSV。例: `squat-rack,dumbbell`",
            examples={
                "any-two": {"value": "squat-rack,dumbbell", "summary": "2種指定"},
                "single": {"value": "smith-machine"},
            },
        ),
    ] = None,
    equipment_match: Annotated[
        Literal["all", "any"],
        Query(
            description="equipments の一致条件",
            examples={"all": {"value": "all"}, "any": {"value": "any"}},
        ),
    ] = "all",
    sort: Annotated[
        Literal["freshness", "richness"],
        Query(
            description="並び替え。freshness は last_verified_at_cached DESC, id ASC。richness は設備スコア降順。",
            examples={"freshness": {"value": "freshness"}, "richness": {"value": "richness"}},
        ),
    ] = "freshness",
    page: Annotated[
        int,
        Query(
            ge=1,
            description="ページ番号（1〜）",
            examples={"first": {"value": 1}},
        ),
    ] = 1,
    per_page: Annotated[
        int,
        Query(
            ge=1, le=50,
            description="1ページ件数（≤50）",
            examples={"ten": {"value": 10}},
        ),
    ] = 20,
    session: AsyncSession = Depends(get_async_session),
):
    # 1) 設備スラッグの取得
    required_slugs: List[str] = get_equipment_slugs_from_query(request, equipments)
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
        return GymSearchResponse(items=[], total=0, has_next=False)
    
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
        # 各設備行のスコア：1.0  min(count,5)*0.1  min(max_weight_kg/60,1)*0.1
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
            slug=g.slug,
            city=g.city,
            pref=g.prefecture,
            last_verified_at_cached=g.last_verified_at_cached.isoformat() if g.last_verified_at_cached else None,
    )
        for g in gyms
    ]
    def _lv(dt: Optional[datetime]):
        # 0001-01-01 等の番兵値を None として返す（必要なら）
        if not dt:
            return None
        if dt.year < 1970:
            return None
        return dt.isoformat()

    items: List[GymSummary] = []
    for g in gyms:
        # GymSummary に必須の slug / city / pref を **忘れずに** 詰める
        items.append(
            GymSummary(
                id=g.id,
                slug=g.slug,
                name=g.name,
                city=g.city,             # モデル: Gym.city
                pref=g.prefecture,       # モデル: Gym.prefecture
                last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
            )
        )

    has_next = (page * per_page) < total
    return GymSearchResponse(items=items, total=total, has_next=has_next)


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
        .order_by(Equipment.name)
    )).all()

    equipments = [
        {
            "equipment_slug": r.equipment_slug,
            "equipment_name": r.equipment_name,
            "category": r.category,
            "count": r.count,
            "max_weight_kg": r.max_weight_kg,
            "last_verified_at": r.last_verified_at,
        }
        for r in rows
    ]
    equipments = []
    for r in rows:
        equipments.append({
            "equipment_slug": r.equipment_slug,
            "equipment_name": r.equipment_name,
            "count": r.count,
            "max_weight_kg": r.max_weight_kg,
        })
    updated_at = max((r.last_verified_at for r in rows if r.last_verified_at), default=None)

    return GymDetailResponse(
            id=gym.id,
            slug=gym.slug,
            name=gym.name,
            city=gym.city,
            pref=gym.prefecture,
            equipments=equipments,
            updated_at=updated_at.isoformat() if updated_at else None,
        )