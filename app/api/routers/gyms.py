# app/api/routers/gyms.py
import base64
import json
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, case, cast, func, literal, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from app.api.deps import get_equipment_slugs_from_query
from app.db import get_async_session
from app.models import Equipment, Gym, GymEquipment
from app.schemas.common import ErrorResponse
from app.schemas.gym_detail import GymDetailResponse
from app.schemas.gym_search import GymSearchResponse, GymSummary

router = APIRouter(prefix="/gyms", tags=["gyms"])


# ---------- Token helpers ----------
def _b64e(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


def _b64d(token: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="invalid page_token")


def _encode_page_token_for_freshness(ts_iso_or_none: str | None, last_id: int) -> str:
    # {sort:'freshness', k:[ts_iso_or_null, id]}
    return _b64e({"sort": "freshness", "k": [ts_iso_or_none, last_id]})


def _encode_page_token_for_richness(nf: int, neg_sc: float, last_id: int) -> str:
    # {sort:'richness', k:[nf, neg_sc, id]}
    return _b64e({"sort": "richness", "k": [nf, neg_sc, last_id]})


def _validate_and_decode_page_token(page_token: str, sort: str) -> tuple:
    payload = _b64d(page_token)
    if payload.get("sort") != sort or "k" not in payload:
        raise HTTPException(status_code=400, detail="invalid page_token")
    k = payload["k"]
    if sort == "freshness" and not (isinstance(k, list) and len(k) == 2):
        raise HTTPException(status_code=400, detail="invalid page_token")
    if sort == "richness" and not (isinstance(k, list) and len(k) == 3):
        raise HTTPException(status_code=400, detail="invalid page_token")
    return tuple(k)  # type: ignore[return-value]


# ---------- DTO helpers ----------
def _lv(dt: datetime | None) -> str | None:
    if not dt or (hasattr(dt, "year") and dt.year < 1970):
        return None
    return dt.isoformat()


def _gym_summary_from_gym(g: Gym) -> GymSummary:
    return GymSummary(
        id=int(getattr(g, "id", 0)),
        slug=str(getattr(g, "slug", "")),
        name=str(getattr(g, "name", "")),
        city=str(getattr(g, "city", "")),
        pref=str(getattr(g, "pref", "")),
        last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
    )


_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順\n"
    " （1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1.0)*0.1）\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
)


@router.get(
    "/search",
    response_model=GymSearchResponse,
    summary="ジム検索（設備フィルタ + Keysetページング）",
    description=_DESC,
    responses={
        400: {
            "description": "Invalid page_token",
            "content": {"application/json": {"example": {"detail": "invalid page_token"}}},
        }
    },
)
async def search_gyms(
    request: Request,
    pref: Annotated[
        str | None,
        Query(description="都道府県スラッグ（lower）例: chiba", examples=["chiba"]),
    ] = None,
    city: Annotated[
        str | None,
        Query(description="市区町村スラッグ（lower）例: funabashi", examples=["funabashi"]),
    ] = None,
    equipments: Annotated[
        str | None,
        Query(
            description="設備スラッグCSV。例: `squat-rack,dumbbell`",
            examples=["squat-rack,dumbbell"],
        ),
    ] = None,
    equipment_match: Annotated[
        Literal["all", "any"],
        Query(description="equipments の一致条件", examples=["all"]),
    ] = "all",
    sort: Annotated[
        Literal["freshness", "richness"],
        Query(
            description="並び替え。freshness は last_verified_at_cached DESC, id ASC。"
            "richness は設備スコア降順",
            examples=["freshness"],
        ),
    ] = "freshness",
    per_page: Annotated[
        int,
        Query(ge=1, le=50, description="1ページ件数（≤50）", examples=[10]),
    ] = 20,
    page_token: str | None = Query(
        None,
        description="前ページから受け取ったKeyset継続トークン（sortと整合しない場合は400）。",
        # 例: {"sort":"freshness","k":[null,42]} のBase64
        examples=["eyJzb3J0IjoiZnJlc2huZXNzIiwiayI6W251bGwsNDJdfQ=="],
    ),
    session: AsyncSession = Depends(get_async_session),
):
    # ---- 1) 設備スラッグの取得 ----
    required_slugs: list[str] = get_equipment_slugs_from_query(request, equipments)
    if equipments and not required_slugs:
        required_slugs = [s.strip() for s in equipments.split(",") if s.strip()]

    # ---- 2) ベース: Gym.id（pref/city を反映） ----
    if pref:
        pref = pref.lower()
    if city:
        city = city.lower()

    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(Gym.pref == pref)
    if city:
        base_ids = base_ids.where(Gym.city == city)

    # ---- 3) 設備フィルタ（all/any）----
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
            base_ids = select(Gym.id).where(Gym.id.in_(ge_grouped_stmt)).where(Gym.id.in_(base_ids))

    # ---- 4) total ----
    total = (await session.scalar(select(func.count()).select_from(base_ids.subquery()))) or 0
    if total == 0:
        return GymSearchResponse(items=[], total=0, has_next=False, page_token=None)

    # ---- 5) 並びと取得 ----
    if sort == "freshness":
        # 列ベースの ORDER（index: pref, city, last_verified_at_cached DESC NULLS LAST, id ASC）
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        # token: [ts_iso_or_null, id]
        lk_ts_iso, lk_id = (None, None)
        if page_token:
            lk_ts_iso, lk_id = _validate_and_decode_page_token(page_token, "freshness")  # type: ignore[misc]
            # 次ページ条件（ts DESC, id ASC）:
            # ts < last_ts OR (ts = last_ts AND id > last_id)
            if lk_ts_iso is None:
                stmt = stmt.where(Gym.last_verified_at_cached.is_(None), Gym.id > int(lk_id))  # type: ignore[arg-type]
            else:
                try:
                    lk_ts = datetime.fromisoformat(lk_ts_iso)  # naive想定
                except Exception:
                    raise HTTPException(status_code=400, detail="invalid page_token")
                stmt = stmt.where(
                    or_(
                        Gym.last_verified_at_cached < lk_ts,
                        and_(Gym.last_verified_at_cached == lk_ts, Gym.id > int(lk_id)),  # type: ignore[arg-type]
                    )
                )

        stmt = stmt.order_by(Gym.last_verified_at_cached.desc().nulls_last(), Gym.id.asc()).limit(
            per_page + 1
        )

        rows = await session.execute(stmt)
        recs = rows.scalars().all()
        gyms = recs[:per_page]

        next_token = None
        if len(recs) > per_page:
            last = recs[per_page - 1]
            ts = getattr(last, "last_verified_at_cached", None)
            ts_iso = ts.isoformat() if ts else None
            next_token = _encode_page_token_for_freshness(ts_iso, last.id)

    else:  # richness
        # スコア式（NULLはnf=1で末尾送り）
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
        # 丸め固定（Numeric(18,6)）し、NULLは大きい値で末尾送り
        neg_sc_expr = cast(func.coalesce(-score, literal(10**9)), Numeric(18, 6))

        stmt = (
            select(Gym, nf_expr.label("nf"), neg_sc_expr.label("neg_sc"))
            .join(score_subq, score_subq.c.gym_id == Gym.id, isouter=True)
            .where(Gym.id.in_(base_ids.scalar_subquery()))
            .order_by("nf", "neg_sc", Gym.id)
            .limit(per_page + 1)
        )

        if page_token:
            lk_nf, lk_neg_sc, lk_id = _validate_and_decode_page_token(page_token, "richness")
            stmt = stmt.where(
                tuple_(nf_expr, neg_sc_expr, Gym.id)
                > tuple_(literal(int(lk_nf)), literal(float(lk_neg_sc)), literal(int(lk_id)))
            )

        rows = await session.execute(stmt)
        recs = rows.all()
        gyms = [r[0] for r in recs[:per_page]]

        next_token = None
        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_richness(
                int(last_row[1]), float(last_row[2]), last_row[0].id
            )

    items: list[GymSummary] = [_gym_summary_from_gym(g) for g in gyms]
    has_next = len(items) == per_page and (total > 0) and (next_token is not None)
    return GymSearchResponse(items=items, total=total, has_next=has_next, page_token=next_token)


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

    rows = (
        await session.execute(
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
        )
    ).all()

    from app.schemas.gym_detail import GymEquipmentLine

    equipments = [
        GymEquipmentLine(
            equipment_slug=str(r.equipment_slug),
            equipment_name=str(r.equipment_name),
            count=getattr(r, "count", None),
            max_weight_kg=getattr(r, "max_weight_kg", None),
        )
        for r in rows
    ]
    updated_at = max((r.last_verified_at for r in rows if r.last_verified_at), default=None)

    return GymDetailResponse(
        id=int(getattr(gym, "id", 0)),
        slug=str(getattr(gym, "slug", "")),
        name=str(getattr(gym, "name", "")),
        city=str(getattr(gym, "city", "")),
        pref=str(getattr(gym, "pref", "")),
        equipments=equipments,
        updated_at=updated_at.isoformat() if updated_at else None,
    )
