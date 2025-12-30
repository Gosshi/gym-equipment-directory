from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from enum import Enum
from typing import Literal

import structlog
from sqlalchemy import and_, case, cast, func, literal, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from app.dto import GymSearchPageDTO, GymSummaryDTO
from app.models import Equipment, Gym, GymEquipment

FRESHNESS_WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))
W_FRESH = float(os.getenv("SCORE_W_FRESH", "0.6"))
W_RICH = float(os.getenv("SCORE_W_RICH", "0.4"))


class GymSortKey(str, Enum):
    gym_name = "gym_name"
    created_at = "created_at"
    freshness = "freshness"
    richness = "richness"
    score = "score"
    distance = "distance"


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


def _encode_page_token_for_distance(distance_km: float, last_id: int) -> str:
    return _b64e(
        {
            "sort": GymSortKey.distance.value,
            "k": [round(float(distance_km), 6), int(last_id)],
        }
    )


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
    if sort == GymSortKey.distance and not (isinstance(k, list) and len(k) == 2):
        raise ValueError("invalid page_token")
    return tuple(k)  # type: ignore[return-value]


def _lv(dt: datetime | None) -> str | None:
    if not dt or (hasattr(dt, "year") and dt.year < 1970):
        return None
    return dt.isoformat()


def _gym_summary_from_gym(g: Gym, *, distance_km: float | None) -> GymSummaryDTO:
    return GymSummaryDTO(
        id=int(getattr(g, "id", 0)),
        slug=str(getattr(g, "slug", "")),
        canonical_id=str(getattr(g, "canonical_id", "")),
        name=str(getattr(g, "name", "")),
        city=str(getattr(g, "city", "")),
        pref=str(getattr(g, "pref", "")),
        official_url=getattr(g, "official_url", None),
        last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
        score=0.0,
        freshness_score=0.0,
        richness_score=0.0,
        distance_km=distance_km,
        latitude=getattr(g, "latitude", None),
        longitude=getattr(g, "longitude", None),
    )


async def search_gyms_api(
    session: AsyncSession,
    *,
    pref: str | None,
    city: str | None,
    lat: float | None,
    lng: float | None,
    radius_km: float | None,
    min_lat: float | None,
    max_lat: float | None,
    min_lng: float | None,
    max_lng: float | None,
    required_slugs: list[str],
    categories: list[str],
    conditions: list[str] | None,
    equipment_match: Literal["all", "any"],
    sort: Literal["freshness", "richness", "gym_name", "created_at", "score", "distance"],
    page: int,
    page_size: int | None,
    page_token: str | None,
) -> GymSearchPageDTO:
    logger = structlog.get_logger(__name__)
    per_page = int(page_size or 20)
    if per_page <= 0:
        per_page = 20
    per_page = max(1, min(per_page, 100))

    current_page = int(page or 1)
    if current_page <= 0:
        current_page = 1
    offset = (current_page - 1) * per_page

    use_keyset = bool(page_token)

    logger.info(
        "gyms_search_begin",
        pref=pref,
        city=city,
        sort=sort,
        page=current_page,
        page_size=per_page,
        use_keyset=use_keyset,
    )
    # ---- 1) ベース: Gym.id（pref/city を反映） ----
    if pref:
        pref = pref.lower()
    if city:
        city = city.lower()

    lat_value = float(lat) if lat is not None else None
    lng_value = float(lng) if lng is not None else None
    radius_value = float(radius_km) if radius_km is not None else None

    if sort == GymSortKey.distance.value and (lat_value is None or lng_value is None):
        raise ValueError("lat/lng are required for distance sort")

    distance_expr = None
    distance_numeric = None
    distance_label = None
    distance_map: dict[int, float] = {}

    base_ids = select(Gym.id)
    if pref:
        base_ids = base_ids.where(Gym.pref == pref)
    if city:
        base_ids = base_ids.where(Gym.city == city)

    if lat_value is not None and lng_value is not None:
        lat1 = func.radians(literal(lat_value))
        lng1 = func.radians(literal(lng_value))
        lat2 = func.radians(Gym.latitude)
        lng2 = func.radians(Gym.longitude)

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = func.pow(func.sin(dlat / 2.0), 2) + func.cos(lat1) * func.cos(lat2) * func.pow(
            func.sin(dlng / 2.0), 2
        )
        c = 2.0 * func.atan2(func.sqrt(a), func.sqrt(func.greatest(0.0, 1.0 - a)))
        distance_expr = 6371.0 * c
        distance_numeric = cast(distance_expr, Numeric(18, 6))
        distance_label = distance_numeric.label("distance_km")

        base_ids = base_ids.where(Gym.latitude.is_not(None), Gym.longitude.is_not(None))
        if radius_value is not None:
            base_ids = base_ids.where(distance_numeric <= radius_value)

    # ---- 1.2) Bounding Box Filter ----
    # Note: Using simple lat/lng comparison. Handles basic cases.
    # For dateline crossing (180/-180), extra logic needed if desired, but Tokyo/Japan is safe.
    if min_lat is not None:
        base_ids = base_ids.where(Gym.latitude >= min_lat)
    if max_lat is not None:
        base_ids = base_ids.where(Gym.latitude <= max_lat)
    if min_lng is not None:
        base_ids = base_ids.where(Gym.longitude >= min_lng)
    if max_lng is not None:
        base_ids = base_ids.where(Gym.longitude <= max_lng)

    # ---- 1.4) 施設カテゴリフィルタ ----
    if categories:
        base_ids = base_ids.where(Gym.categories.overlap(categories))

    # ---- 1.5) 条件フィルタ (parsed_json) ----
    if conditions:
        for cond in conditions:
            # {"tags": [cond]} OR {cond: true}
            tag_match = Gym.parsed_json.contains({"tags": [cond]})
            bool_match = Gym.parsed_json.contains({cond: True})
            base_ids = base_ids.where(or_(tag_match, bool_match))

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
        return GymSearchPageDTO(
            items=[],
            total=0,
            page=current_page,
            page_size=per_page,
            has_more=False,
            has_prev=current_page > 1,
            page_token=None,
        )

    # ---- 4) 並びと取得 ----
    next_token = None
    gyms: list[Gym] = []
    scored_rows = None

    if sort == "freshness":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        if use_keyset and page_token:
            lk_ts_iso, lk_id = _validate_and_decode_page_token(page_token, "freshness")  # type: ignore[misc]
            if lk_ts_iso is None:
                stmt = stmt.where(
                    Gym.last_verified_at_cached.is_(None),
                    Gym.id > int(lk_id),  # type: ignore[arg-type]
                )
            else:
                try:
                    lk_ts = datetime.fromisoformat(lk_ts_iso)
                except Exception as exc:  # noqa: BLE001
                    raise ValueError("invalid page_token") from exc
                stmt = stmt.where(
                    or_(
                        Gym.last_verified_at_cached < lk_ts,
                        and_(
                            Gym.last_verified_at_cached == lk_ts,
                            Gym.id > int(lk_id),  # type: ignore[arg-type]
                        ),
                    )
                )

        if distance_label is not None:
            stmt = stmt.add_columns(distance_label)

        stmt = stmt.order_by(Gym.last_verified_at_cached.desc().nulls_last(), Gym.id.asc())
        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)

        rows = await session.execute(stmt)
        recs = rows.all()
        page_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in page_rows]

        if distance_label is not None:
            for row in page_rows:
                dist_val = getattr(row, "distance_km", None)
                if dist_val is not None:
                    distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            last = last_row[0]
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
        )

        if use_keyset and page_token:
            lk_nf, lk_neg_sc, lk_id = _validate_and_decode_page_token(page_token, "richness")
            stmt = stmt.where(
                tuple_(nf_expr, neg_sc_expr, Gym.id)
                > tuple_(literal(int(lk_nf)), literal(float(lk_neg_sc)), literal(int(lk_id)))
            )

        if distance_label is not None:
            stmt = stmt.add_columns(distance_label)

        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)

        rows = await session.execute(stmt)
        recs = rows.all()
        page_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in page_rows]

        if distance_label is not None:
            for row in page_rows:
                dist_val = getattr(row, "distance_km", None)
                if dist_val is not None:
                    distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_richness(
                int(getattr(last_row, "nf")),
                float(getattr(last_row, "neg_sc")),
                last_row[0].id,
            )
    elif sort == "gym_name":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        if use_keyset and page_token:
            last_name, last_id = _validate_and_decode_page_token(page_token, "gym_name")  # type: ignore[misc]
            stmt = stmt.where(
                or_(
                    Gym.name > str(last_name),
                    and_(Gym.name == str(last_name), Gym.id > int(last_id)),  # type: ignore[arg-type]
                )
            )
        if distance_label is not None:
            stmt = stmt.add_columns(distance_label)

        stmt = stmt.order_by(Gym.name.asc(), Gym.id.asc())
        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)
        rows = await session.execute(stmt)
        recs = rows.all()
        page_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in page_rows]

        if distance_label is not None:
            for row in page_rows:
                dist_val = getattr(row, "distance_km", None)
                if dist_val is not None:
                    distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            last = last_row[0]
            next_token = _encode_page_token_for_gym_name(
                str(getattr(last, "name", "")), int(getattr(last, "id", 0))
            )

    elif sort == "created_at":
        stmt = select(Gym).where(Gym.id.in_(base_ids.scalar_subquery()))
        if use_keyset and page_token:
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
        if distance_label is not None:
            stmt = stmt.add_columns(distance_label)

        stmt = stmt.order_by(Gym.created_at.desc(), Gym.id.asc())
        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)
        rows = await session.execute(stmt)
        recs = rows.all()
        page_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in page_rows]

        if distance_label is not None:
            for row in page_rows:
                dist_val = getattr(row, "distance_km", None)
                if dist_val is not None:
                    distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            last = last_row[0]
            ts = getattr(last, "created_at", None)
            ts_iso = ts.isoformat() if ts else datetime.now().isoformat()
            next_token = _encode_page_token_for_created_at(ts_iso, int(getattr(last, "id", 0)))
    elif sort == "distance":
        if distance_label is None or distance_numeric is None:
            raise ValueError("lat/lng are required for distance sort")

        stmt = select(Gym, distance_label).where(Gym.id.in_(base_ids.scalar_subquery()))

        if use_keyset and page_token:
            lk_dist, lk_id = _validate_and_decode_page_token(page_token, "distance")
            stmt = stmt.where(
                tuple_(distance_numeric, Gym.id)
                > tuple_(literal(float(lk_dist)), literal(int(lk_id)))
            )

        stmt = stmt.order_by(distance_numeric.asc(), Gym.id.asc())
        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)

        rows = await session.execute(stmt)
        recs = rows.all()
        page_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in page_rows]

        for row in page_rows:
            dist_val = getattr(row, "distance_km", None)
            if dist_val is not None:
                distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_distance(
                float(getattr(last_row, "distance_km")), int(getattr(last_row[0], "id", 0))
            )
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
        )

        if use_keyset and page_token:
            lk_neg_final, lk_id = _validate_and_decode_page_token(page_token, "score")
            stmt = stmt.where(
                tuple_(neg_final, Gym.id)
                > tuple_(literal(float(lk_neg_final)), literal(int(lk_id)))
            )

        if distance_label is not None:
            stmt = stmt.add_columns(distance_label)

        if use_keyset:
            stmt = stmt.limit(per_page + 1)
        else:
            stmt = stmt.offset(offset).limit(per_page)

        rows = await session.execute(stmt)
        recs = rows.all()
        scored_rows = recs[:per_page] if use_keyset else recs
        gyms = [r[0] for r in scored_rows]

        if distance_label is not None:
            for row in scored_rows:
                dist_val = getattr(row, "distance_km", None)
                if dist_val is not None:
                    distance_map[int(getattr(row[0], "id", 0))] = float(dist_val)

        if use_keyset and len(recs) > per_page:
            last_row = recs[per_page - 1]
            next_token = _encode_page_token_for_score(
                float(last_row.neg_final), int(last_row.Gym.id)
            )

    # ---- 5) マッピング ----
    if sort != "score":
        items: list[GymSummaryDTO] = [
            _gym_summary_from_gym(
                g,
                distance_km=distance_map.get(int(getattr(g, "id", 0))),
            )
            for g in gyms
        ]
    else:
        items = []
        for row in scored_rows or []:
            g = row[0]
            gid = int(getattr(g, "id", 0))
            items.append(
                GymSummaryDTO(
                    id=gid,
                    slug=str(getattr(g, "slug", "")),
                    canonical_id=str(getattr(g, "canonical_id", "")),
                    name=str(getattr(g, "name", "")),
                    city=str(getattr(g, "city", "")),
                    pref=str(getattr(g, "pref", "")),
                    official_url=getattr(g, "official_url", None),
                    last_verified_at=_lv(getattr(g, "last_verified_at_cached", None)),
                    score=float(row.score or 0.0),
                    freshness_score=float(row.freshness_score or 0.0),
                    richness_score=float(row.richness_score or 0.0),
                    distance_km=distance_map.get(gid),
                    latitude=getattr(g, "latitude", None),
                    longitude=getattr(g, "longitude", None),
                )
            )

    if use_keyset:
        has_more = bool(next_token) and len(items) == per_page
        has_prev = current_page > 1 or bool(page_token)
    else:
        has_more = (offset + len(items)) < total
        has_prev = offset > 0
        next_token = None

    logger.info(
        "gyms_search_end",
        count=len(items),
        has_more=bool(has_more),
        page=current_page,
        page_size=per_page,
        total=total,
    )
    return GymSearchPageDTO(
        items=items,
        total=total,
        page=current_page,
        page_size=per_page,
        has_more=has_more,
        has_prev=has_prev,
        page_token=next_token,
    )
