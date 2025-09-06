# app/api/routers/gyms.py
from typing import Literal, Optional, List
from typing_extensions import Annotated
from datetime import datetime
import base64
import json

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select, func, case, literal, and_, or_, tuple_, asc, desc, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

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
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="invalid page_token")

# page_tokenの検証とデコード
def _validate_and_decode_page_token(page_token: str, sort: str) -> tuple | None:
    if not page_token:
        return None
    try:
        payload = _decode_page_token(page_token)
        if payload.get("sort") != sort:
            raise HTTPException(status_code=400, detail="invalid page_token")
        return tuple(payload["k"])
    except Exception:
        raise HTTPException(status_code=400, detail="invalid page_token")

# GymSummary生成の共通化
def _get_value(val, name=None):
    # SQLAlchemy Column型ならインスタンスから値を取得
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    if isinstance(val, InstrumentedAttribute) and name:
        # g.id などがColumn型の場合、g.__getattribute__('id') で値を取得
        return val.parent.__getattribute__(name)
    if hasattr(val, 'value'):
        return val.value
    if callable(val):
        return val()
    return val

def _gym_summary_from_gym(g: Gym) -> GymSummary:
    def _lv(dt: Optional[datetime]):
        if not dt or (hasattr(dt, 'year') and dt.year < 1970):
            return None
        return dt.isoformat()
    return GymSummary(
        id=int(getattr(g, 'id', 0)),
        slug=str(getattr(g, 'slug', '')),
        name=str(getattr(g, 'name', '')),
        city=str(getattr(g, 'city', '')),
        pref=str(getattr(g, 'pref', '')),
        last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
    )


_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順（1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1.0)*0.1）\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
)


@router.get(
    "/search",
    response_model=GymSearchResponse,
    summary="ジム検索（設備フィルタ  ページング）",
    description=_DESC,
    responses={
        400: {
            "description": "Invalid page_token",
            "content": {"application/json": {"example": {"detail": "invalid page_token"}}},
        }
    }
)
async def search_gyms(
    request: Request,
    pref: Annotated[
        Optional[str],
        Query(
            description="都道府県スラッグ（lower）例: chiba",
            example="chiba",
        ),
    ] = None,
    city: Annotated[
        Optional[str],
        Query(
            description="市区町村スラッグ（lower）例: funabashi",
            example="funabashi",
        ),
    ] = None,
    equipments: Annotated[
        Optional[str],
        Query(
            description="設備スラッグCSV。例: `squat-rack,dumbbell`",
            example="squat-rack,dumbbell",
        ),
    ] = None,
    equipment_match: Annotated[
        Literal["all", "any"],
        Query(
            description="equipments の一致条件",
            example="all",
        ),
    ] = "all",
    sort: Annotated[
        Literal["freshness", "richness"],
        Query(
            description="並び替え。freshness は last_verified_at_cached DESC, id ASC。richness は設備スコア降順。",
            example="freshness",
        ),
    ] = "freshness",
    per_page: Annotated[
        int,
        Query(
            ge=1, le=50,
            description="1ページ件数（≤50）",
            example=10,
        ),
    ] = 20,
    page_token: str | None = Query(
        None,
        description="前ページから受け取ったKeyset継続トークン（sortと整合しない場合は400）。",
        example="v1:freshness:nf=0,ts=1725555555,id=42",
    ),
    session: AsyncSession = Depends(get_async_session),
):
    # page_tokenの整合性チェックとデコード
    last_key = _validate_and_decode_page_token(page_token, sort) if page_token else None

    # 1) 設備スラッグの取得
    required_slugs: List[str] = get_equipment_slugs_from_query(
        request, equipments)

    if equipments and not required_slugs:
        required_slugs = [s.strip()
                          for s in equipments.split(",") if s.strip()]

    # 2) ベース: Gym.id（pref/city を反映）
    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(func.lower(Gym.pref) == func.lower(pref))
    if city:
        base_ids = base_ids.where(func.lower(Gym.city) == func.lower(city))

    # 3) 設備フィルタ（all/any）
    if required_slugs:
        eq_ids_stmt = select(Equipment.id).where(
            Equipment.slug.in_(required_slugs))

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
        return GymSearchResponse(items=[], total=0, has_next=False, page_token=None)

    # last_keyは上記で取得済み

    # 5) 並びと取得
    if sort == "freshness":
        nf_expr = case(
            (Gym.last_verified_at_cached.is_(None), 1),
            (func.extract('epoch', Gym.last_verified_at_cached) < 0, 1),
            else_=0
        )
        neg_ep_expr = func.coalesce(-func.extract('epoch', Gym.last_verified_at_cached), literal(10**18))
        stmt = select(Gym, nf_expr.label("nf"), neg_ep_expr.label("neg_ep")).where(
            Gym.id.in_(select(base_ids.subquery().c.id))
        )
        if last_key:
            lk_nf, lk_neg_ep, lk_id = last_key
            stmt = stmt.where(
                tuple_(nf_expr, neg_ep_expr, Gym.id) >
                tuple_(literal(lk_nf), literal(lk_neg_ep), literal(lk_id))
            )
        rows = await session.execute(
            stmt.order_by("nf", "neg_ep", Gym.id).limit(per_page + 1)
        )
        recs = rows.all()
        gyms = [r[0] for r in recs[:per_page]]
        next_token = None
        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            last_nf = int(last_row[1])
            last_neg_ep = float(last_row[2])
            next_token = _encode_page_token((last_nf, last_neg_ep, last_row[0].id), "freshness")
    else:  # richness
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
        score = score_subq.c.score
        nf_expr = case((score.is_(None), 1), else_=0)
        neg_sc_expr = cast(func.coalesce(-score, literal(10**9)), Numeric(18, 6))
        stmt = (
            select(
                Gym,
                nf_expr.label("nf"),
                neg_sc_expr.label("neg_sc"),
            )
            .join(score_subq, score_subq.c.gym_id == Gym.id, isouter=True)
            .where(Gym.id.in_(select(base_ids.subquery().c.id)))
        )
        if last_key:
            lk_nf, lk_neg_sc, lk_id = last_key
            stmt = stmt.where(
                tuple_(nf_expr, neg_sc_expr, Gym.id) >
                tuple_(literal(int(lk_nf)), literal(float(lk_neg_sc)), literal(int(lk_id)))
            )
        rows = await session.execute(
            stmt.order_by("nf", "neg_sc", Gym.id).limit(per_page + 1)
        )
        recs = rows.all()
        gyms = [r[0] for r in recs[:per_page]]
        next_token = None
        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token((int(last_row[1]), float(last_row[2]), last_row[0].id), "richness")

    def _lv(dt: Optional[datetime]):
        # SQL 側の “epoch<0 は NULL扱い” と合わせる
        if not dt:
            return None
        if dt.year < 1970:
            return None
        return dt.isoformat()

    items: List[GymSummary] = [_gym_summary_from_gym(g) for g in gyms]
    has_next = len(items) == per_page and (total > 0) and (next_token is not None)
    return GymSearchResponse(items=items, total=total, has_next=has_next, page_token=next_token)


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

    from app.schemas.gym_detail import GymEquipmentLine
    equipments = [
        GymEquipmentLine(
            equipment_slug=str(r.equipment_slug),
            equipment_name=str(r.equipment_name),
            count=getattr(r, 'count', None) if not callable(getattr(r, 'count', None)) else None,
            max_weight_kg=getattr(r, 'max_weight_kg', None)
        )
        for r in rows
    ]
    updated_at = max(
        (r.last_verified_at for r in rows if r.last_verified_at), default=None)

    return GymDetailResponse(
        id=int(getattr(gym, 'id', 0)),
        slug=str(getattr(gym, 'slug', '')),
        name=str(getattr(gym, 'name', '')),
        city=str(getattr(gym, 'city', '')),
        pref=str(getattr(gym, 'pref', '')),
        equipments=equipments,
        updated_at=updated_at.isoformat() if updated_at else None,
    )
