from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from enum import StrEnum
from typing import Literal

from sqlalchemy import and_, case, cast, func, literal, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from app.models import Equipment, Gym, GymEquipment
from app.schemas.gym_search import GymSearchResponse, GymSummary

FRESHNESS_WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))
W_FRESH = float(os.getenv("SCORE_W_FRESH", "0.6"))
W_RICH = float(os.getenv("SCORE_W_RICH", "0.4"))


class GymSortKey(StrEnum):
    gym_name = "gym_name"
    created_at = "created_at"
    freshness = "freshness"
    richness = "richness"
    score = "score"


def _b64e(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


def _b64d(token: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid page_token") from exc


def _encode_page_token_for_freshness(ts_iso_or_none: str | None, last_id: int) -> str:
    return _b64e({"sort": GymSortKey.freshness.value, "k": [ts_iso_or_none, last_id]})


def _encode_page_token_for_richness(nf: int, neg_sc: float, last_id: int) -> str:
    return _b64e({"sort": GymSortKey.richness.value, "k": [nf, neg_sc, last_id]})


def _encode_page_token_for_gym_name(last_name: str, last_id: int) -> str:
    return _b64e({"sort": GymSortKey.gym_name.value, "k": [last_name, last_id]})


def _encode_page_token_for_created_at(ts_iso: str, last_id: int) -> str:
    return _b64e({"sort": GymSortKey.created_at.value, "k": [ts_iso, last_id]})


def _encode_page_token_for_score(score: float, last_id: int) -> str:
    return _b64e({"sort": GymSortKey.score.value, "k": [score, last_id]})


def _validate_and_decode_page_token(page_token: str, sort: str) -> tuple:
    payload = _b64d(page_token)
    s = str(payload.get("sort"))
    if not (s == sort or s.endswith("." + sort)) or "k" not in payload:
        raise ValueError("invalid page_token")
    k = payload["k"]
    if sort == GymSortKey.freshness and not (isinstance(k, list) and len(k) == 2):
        raise ValueError("invalid page_token")
    if sort == GymSortKey.richness and not (isinstance(k, list) and len(k) == 3):
        raise ValueError("invalid page_token")
    if sort == GymSortKey.gym_name and not (
        isinstance(k, list) and len(k) == 2 and isinstance(k[0], str)
    ):
        raise ValueError("invalid page_token")
    if sort == GymSortKey.created_at and not (
        isinstance(k, list) and len(k) == 2 and isinstance(k[0], str)
    ):
        raise ValueError("invalid page_token")
    if sort == GymSortKey.score and not (isinstance(k, list) and len(k) == 2):
        raise ValueError("invalid page_token")
    return tuple(k)  # type: ignore[return-value]


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


async def search_gyms_api(
    session: AsyncSession,
    *,
    pref: str | None,
    city: str | None,
    required_slugs: list[str],
    equipment_match: Literal["all", "any"],
    sort: Literal["freshness", "richness", "gym_name", "created_at", "score"],
    per_page: int,
    page_token: str | None,
) -> GymSearchResponse:
    # ---- 1) ベース: Gym.id（pref/city を反映） ----
    if pref:
        pref = pref.lower()
    if city:
        city = city.lower()

    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(Gym.pref == pref)
    if city:
        base_ids = base_ids.where(Gym.city == city)

    # ---- 2) 設備フィルタ（all/any）----
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

    # ---- 3) total ----
    total = (await session.scalar(select(func.count()).select_from(base_ids.subquery()))) or 0
    if total == 0:
        return GymSearchResponse(items=[], total=0, has_next=False, page_token=None)

    # ---- 4) 並びと取得 ----
    next_token = None
    gyms: list[Gym] = []
    scored_rows = None

    if sort == "freshness":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        lk_ts_iso, lk_id = (None, None)
        if page_token:
            lk_ts_iso, lk_id = _validate_and_decode_page_token(page_token, "freshness")  # type: ignore[misc]
            if lk_ts_iso is None:
                stmt = stmt.where(Gym.last_verified_at_cached.is_(None), Gym.id > int(lk_id))  # type: ignore[arg-type]
            else:
                try:
                    lk_ts = datetime.fromisoformat(lk_ts_iso)  # naive想定
                except Exception as exc:  # noqa: BLE001
                    raise ValueError("invalid page_token") from exc
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

        if len(recs) > per_page:
            last = recs[per_page - 1]
            ts = getattr(last, "last_verified_at_cached", None)
            ts_iso = ts.isoformat() if ts else None
            next_token = _encode_page_token_for_freshness(ts_iso, int(getattr(last, "id", 0)))

    elif sort == "richness":
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

        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_richness(
                int(last_row[1]), float(last_row[2]), last_row[0].id
            )
    elif sort == "gym_name":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        last_name, last_id = (None, None)
        if page_token:
            last_name, last_id = _validate_and_decode_page_token(page_token, "gym_name")  # type: ignore[misc]
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
        if len(recs) > per_page:
            last = recs[per_page - 1]
            next_token = _encode_page_token_for_gym_name(
                str(getattr(last, "name", "")), int(getattr(last, "id", 0))
            )

    elif sort == "created_at":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        lk_ts_iso, lk_id = (None, None)
        if page_token:
            lk_ts_iso, lk_id = _validate_and_decode_page_token(page_token, "created_at")  # type: ignore[misc]
            try:
                lk_ts = datetime.fromisoformat(str(lk_ts_iso))
            except Exception as exc:  # noqa: BLE001
                raise ValueError("invalid page_token") from exc
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
        if len(recs) > per_page:
            last = recs[per_page - 1]
            ts = getattr(last, "created_at", None)
            ts_iso = ts.isoformat() if ts else datetime.now().isoformat()
            next_token = _encode_page_token_for_created_at(ts_iso, int(getattr(last, "id", 0)))
    elif sort == "score":
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
            (is_finite_ts.is_(False), cast(0.0, Numeric(10, 6))),
            else_=cast(
                func.greatest(0.0, func.least(1.0, freshness_linear)),
                Numeric(10, 6),
            ),
        )

        final_score = cast(W_FRESH * freshness + W_RICH * richness_norm, Numeric(10, 6))
        neg_final = cast(-final_score, Numeric(18, 6))

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

        if len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_score(
                float(last_row.neg_final), int(last_row.Gym.id)
            )

    # ---- 5) マッピング ----
    if sort != "score":
        items: list[GymSummary] = [_gym_summary_from_gym(g) for g in gyms]
    else:
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
