# app/api/routers/gyms.py
import base64
import json
import os
from datetime import datetime
from enum import Enum
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
from app.services.scoring import compute_bundle

router = APIRouter(prefix="/gyms", tags=["gyms"])

FRESHNESS_WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))
W_FRESH = float(os.getenv("SCORE_W_FRESH", "0.6"))
W_RICH = float(os.getenv("SCORE_W_RICH", "0.4"))


class GymSortKey(str, Enum):
    gym_name = "gym_name"
    created_at = "created_at"
    freshness = "freshness"
    richness = "richness"
    score = "score"


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
    return _b64e({"sort": GymSortKey.freshness.value, "k": [ts_iso_or_none, last_id]})


def _encode_page_token_for_richness(nf: int, neg_sc: float, last_id: int) -> str:
    # {sort:'richness', k:[nf, neg_sc, id]}
    return _b64e({"sort": GymSortKey.richness.value, "k": [nf, neg_sc, last_id]})


def _encode_page_token_for_gym_name(last_name: str, last_id: int) -> str:
    # {sort:'gym_name', k:[last_name, id]}
    return _b64e({"sort": GymSortKey.gym_name.value, "k": [last_name, last_id]})


def _encode_page_token_for_created_at(ts_iso: str, last_id: int) -> str:
    # {sort:'created_at', k:[ts_iso, id]}
    return _b64e({"sort": GymSortKey.created_at.value, "k": [ts_iso, last_id]})


def _encode_page_token_for_score(score: float, last_id: int) -> str:
    # {sort:'score', k:[score, id]}
    return _b64e({"sort": GymSortKey.score.value, "k": [score, last_id]})


def _validate_and_decode_page_token(page_token: str, sort: str) -> tuple:
    payload = _b64d(page_token)
    s = str(payload.get("sort"))
    # "score" も "GymSortKey.score" もOKにする
    if not (s == sort or s.endswith("." + sort)) or "k" not in payload:
        raise HTTPException(status_code=400, detail="invalid page_token")
    k = payload["k"]
    if sort == GymSortKey.freshness and not (isinstance(k, list) and len(k) == 2):
        raise HTTPException(status_code=400, detail="invalid page_token")
    if sort == GymSortKey.richness and not (isinstance(k, list) and len(k) == 3):
        raise HTTPException(status_code=400, detail="invalid page_token")
    if sort == GymSortKey.gym_name and not (
        isinstance(k, list) and len(k) == 2 and isinstance(k[0], str)
    ):
        raise HTTPException(status_code=400, detail="invalid page_token")
    if sort == GymSortKey.created_at and not (
        isinstance(k, list) and len(k) == 2 and isinstance(k[0], str)
    ):
        raise HTTPException(status_code=400, detail="invalid page_token")
    if sort == GymSortKey.score and not (
        isinstance(k, list) and len(k) == 2
        # k[0] は neg_final（数値）、k[1] は id（数値）を想定。厳密チェックしたいなら下を有効化。
        # and isinstance(k[0], (int, float)) and isinstance(k[1], (int, float))
    ):
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
        score=0.0,
        freshness_score=0.0,
        richness_score=0.0,
    )


_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順\n"
    " （1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1.0)*0.1）\n"
    " - sort=score: freshness(0.6)とrichness(0.4)を合算した最終スコア降順\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
    "- sort=gym_name: name ASC, id ASC（Keyset）\n"
    "- sort=created_at: created_at DESC, id ASC（Keyset）\n"
)


async def _count_equips(sess: AsyncSession, gym_id: int) -> int:
    q = select(func.count()).select_from(GymEquipment).where(GymEquipment.gym_id == gym_id)
    return (await sess.execute(q)).scalar_one()


async def _max_gym_equips(sess: AsyncSession) -> int:
    """全ジム中の最大設備点数。小規模環境では都度計算、将来はキャッシュ/別テーブルへ。"""
    sub = (
        select(GymEquipment.gym_id, func.count().label("c"))
        .group_by(GymEquipment.gym_id)
        .subquery()
    )
    q = select(func.coalesce(func.max(sub.c.c), 0))
    return (await sess.execute(q)).scalar_one()


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
        Literal["freshness", "richness", "gym_name", "created_at", "score"],
        Query(
            description="並び替え。freshness は last_verified_at_cached DESC, id ASC。"
            "richness は設備スコア降順"
            "score は freshness(0.6) + richness(0.4) の降順。"
            "gym_name は name ASC, id ASC"
            "created_at は created_at DESC, id ASC",
            examples=["freshness", "gym_name"],
        ),
    ] = "score",
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
    next_token = None  # [must] すべての分岐で next_token を初期化
    gyms = []  # [must] すべての分岐で gyms を初期化
    scored_rows = None

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
            next_token = _encode_page_token_for_freshness(ts_iso, int(getattr(last, "id", 0)))

    elif sort == "richness":  # richness
        # スコア式（NULLはnf=1で末尾送り）
        # 1) page_token のソート種別を先に検証（ミスマッチなら 400）
        lk_nf = lk_neg_sc = lk_id = None
        if page_token:
            lk_nf, lk_neg_sc, lk_id = _validate_and_decode_page_token(page_token, "richness")

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
            .order_by(nf_expr, neg_sc_expr, Gym.id)
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
    elif sort == "gym_name":
        # name ASC, id ASC（Keyset）
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        last_name, last_id = (None, None)
        if page_token:
            last_name, last_id = _validate_and_decode_page_token(page_token, "gym_name")  # type: ignore[misc]
            # 次ページ条件（name ASC, id ASC）:
            # name > last_name OR (name = last_name AND id > last_id)
            stmt = stmt.where(
                or_(
                    Gym.name > str(last_name),
                    and_(Gym.name == str(last_name), Gym.id > int(last_id)),  # type: ignore[arg-type]
                )
            )
        stmt = stmt.order_by(Gym.name.asc(), Gym.id.asc()).limit(per_page + 1)
        rows = await session.execute(stmt)
        recs = rows.scalars().all()
        gyms = recs[:per_page]
        next_token = None
        if len(recs) > per_page:
            last = recs[per_page - 1]
            next_token = _encode_page_token_for_gym_name(
                str(getattr(last, "name", "")), int(getattr(last, "id", 0))
            )

    elif sort == "created_at":
        # created_at DESC（新着順）, id ASC（Keyset）
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        lk_ts_iso, lk_id = (None, None)
        if page_token:
            lk_ts_iso, lk_id = _validate_and_decode_page_token(page_token, "created_at")  # type: ignore[misc]
            try:
                lk_ts = datetime.fromisoformat(str(lk_ts_iso))
            except Exception:
                raise HTTPException(status_code=400, detail="invalid page_token")
            # 次ページ条件（created_at DESC, id ASC）:
            # created_at < last_ts OR (created_at = last_ts AND id > last_id)
            stmt = stmt.where(
                or_(
                    Gym.created_at < lk_ts,
                    and_(Gym.created_at == lk_ts, Gym.id > int(lk_id)),  # type: ignore[arg-type]
                )
            )
        stmt = stmt.order_by(Gym.created_at.desc(), Gym.id.asc()).limit(per_page + 1)
        rows = await session.execute(stmt)
        recs = rows.scalars().all()
        gyms = recs[:per_page]
        next_token = None
        if len(recs) > per_page:
            last = recs[per_page - 1]
            ts = getattr(last, "created_at", None)
            ts_iso = ts.isoformat() if ts else datetime.now().isoformat()
            next_token = _encode_page_token_for_created_at(ts_iso, int(getattr(last, "id", 0)))
    elif sort == "score":
        # ❶ richness（既存の「合算スコア」）を 0..1 に正規化
        score_expr = (
            1.0
            + func.least(func.coalesce(GymEquipment.count, 0), 5) * 0.1
            + func.least(func.coalesce(GymEquipment.max_weight_kg, 0) / 60.0, 1.0) * 0.1
        )
        score_subq = (
            select(
                GymEquipment.gym_id.label("gym_id"),
                func.sum(score_expr).label("raw_richness"),
            )
            .select_from(GymEquipment)
            .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        )
        if required_slugs:
            score_subq = score_subq.where(Equipment.slug.in_(required_slugs))
        score_subq = score_subq.group_by(GymEquipment.gym_id).subquery()

        raw_richness = func.coalesce(score_subq.c.raw_richness, 0.0)
        # ★ window を使わず、全体最大をスカラ副問い合わせで取得
        richness_max_scalar = (
            select(func.max(func.coalesce(score_subq.c.raw_richness, 0.0)))
        ).scalar_subquery()
        richness_norm = case(
            (
                richness_max_scalar > 0.0,
                cast(raw_richness / cast(richness_max_scalar, Numeric(10, 6)), Numeric(10, 6)),
            ),
            else_=cast(0.0, Numeric(10, 6)),
        )

        # ❷ freshness（0..1）: last_verified_at_cached を 365 日で線形減衰
        #   ※ ±infinity を避けるため isfinite() でガード
        is_finite_ts = func.isfinite(Gym.last_verified_at_cached)
        age_days = case(
            (
                is_finite_ts,
                func.extract("epoch", func.now() - Gym.last_verified_at_cached) / 86400.0,
            ),
            else_=None,
        )
        freshness_linear = 1.0 - (cast(age_days, Numeric(10, 6)) / float(FRESHNESS_WINDOW_DAYS))
        freshness = case(
            # NULL / ±infinity → 0.0
            (is_finite_ts.is_(False), cast(0.0, Numeric(10, 6))),
            else_=cast(
                func.greatest(0.0, func.least(1.0, freshness_linear)),
                Numeric(10, 6),
            ),
        )

        # ❸ final score
        final_score = cast(W_FRESH * freshness + W_RICH * richness_norm, Numeric(10, 6))
        neg_final = cast(-final_score, Numeric(18, 6))  # ASC で keyset するため符号反転

        stmt = (
            select(
                Gym,
                func.round(final_score, 3).label("score"),
                func.round(freshness, 3).label("freshness_score"),
                func.round(richness_norm, 3).label("richness_score"),
                neg_final.label("neg_final"),
            )
            .join(score_subq, score_subq.c.gym_id == Gym.id, isouter=True)
            .where(Gym.id.in_(base_ids.scalar_subquery()))
            .order_by(neg_final.asc(), Gym.id.asc())
            .limit(per_page + 1)
        )

        # page_token: [neg_final, id]
        if page_token:
            lk_neg_final, lk_id = _validate_and_decode_page_token(page_token, "score")
            stmt = stmt.where(
                tuple_(neg_final, Gym.id)
                > tuple_(literal(float(lk_neg_final)), literal(int(lk_id)))
            )

        rows = await session.execute(stmt)
        recs = rows.all()
        scored_rows = recs[:per_page]
        gyms = [r[0] for r in scored_rows]

        next_token = None
        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_score(
                float(last_row.neg_final), int(last_row.Gym.id)
            )

    items: list[GymSummary] = [_gym_summary_from_gym(g) for g in gyms]
    # 通常分岐
    if sort != "score":
        items: list[GymSummary] = [_gym_summary_from_gym(g) for g in gyms]
    else:
        # score 分岐は、各行の追加列を GymSummary に詰める
        items = []
        for row in scored_rows or []:
            g = row[0]
            items.append(
                GymSummary(
                    id=int(getattr(g, "id", 0)),
                    slug=str(getattr(g, "slug", "")),
                    name=str(getattr(g, "name", "")),
                    city=str(getattr(g, "city", "")),
                    pref=str(getattr(g, "pref", "")),
                    last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
                    score=float(row.score or 0.0),
                    freshness_score=float(row.freshness_score or 0.0),
                    richness_score=float(row.richness_score or 0.0),
                )
            )
    has_next = len(items) == per_page and (total > 0) and (next_token is not None)
    if not has_next:
        next_token = None
    return GymSearchResponse(items=items, total=total, has_next=has_next, page_token=next_token)


@router.get(
    "/{slug}",
    response_model=GymDetailResponse,
    summary="ジム詳細を取得",
    description=(
        "ジム詳細を返却します。`include=score` を指定すると freshness/richness/score を同梱します。"
    ),
    responses={404: {"model": ErrorResponse, "description": "ジムが見つかりません"}},
)
async def get_gym_detail(
    slug: str,
    include: str | None = Query(default=None, description="例: include=score"),
    session: AsyncSession = Depends(get_async_session),
):
    gym = (await session.execute(select(Gym).where(Gym.slug == slug))).scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="gym not found")
    # --- equipments を JOIN して配列に構築 ---
    eq_rows = await session.execute(
        select(
            Equipment.slug,
            Equipment.name,
            Equipment.category,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
        )
        .join(GymEquipment, GymEquipment.equipment_id == Equipment.id)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.name)
    )
    equipments_list = [
        {
            "equipment_slug": slug,
            "equipment_name": name,
            "category": category,
            "count": count,
            "max_weight_kg": max_w,
        }
        for (slug, name, category, count, max_w) in eq_rows.all()
    ]

    # Pydantic v2: 必要キーを手組みしてから validate
    # 必須フィールドを明示的に埋めてから validate（Pydantic v2）
    data = {
        "id": gym.id,
        "slug": gym.slug,
        "name": gym.name,
        "pref": getattr(gym, "pref", None),
        "city": gym.city,
        # 必須の updated_at / last_verified_at は ISO 文字列に統一
        "updated_at": gym.updated_at.isoformat() if getattr(gym, "updated_at", None) else None,
        "last_verified_at": gym.last_verified_at_cached.isoformat()
        if getattr(gym, "last_verified_at_cached", None)
        else None,
        # スキーマの item 形に合わせた dict 配列
        "equipments": equipments_list,
    }

    if include == "score":
        num = await _count_equips(session, int(getattr(gym, "id", 0)))
        mx = await _max_gym_equips(session)
        bundle = compute_bundle(gym.last_verified_at_cached, num, mx)
        # 追加フィールドを dict に積む
        data["freshness"] = bundle.freshness
        data["richness"] = bundle.richness
        data["score"] = bundle.score

    return GymDetailResponse.model_validate(data)
