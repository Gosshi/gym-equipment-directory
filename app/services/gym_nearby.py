from __future__ import annotations

import base64
import json
from datetime import datetime

import structlog
from sqlalchemy import and_, cast, func, literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from app.models.gym import Gym
from app.schemas.gym_nearby import GymNearbyItem, GymNearbyResponse


def _b64e(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


def _b64d(token: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid page_token") from exc


def _encode_page_token_for_nearby(distance_km: float, last_id: int) -> str:
    # Round to 6 decimals for stability in comparisons
    return _b64e({"sort": "nearby", "k": [round(float(distance_km), 6), int(last_id)]})


def _validate_and_decode_page_token(page_token: str) -> tuple[float, int]:
    payload = _b64d(page_token)
    if str(payload.get("sort")) not in ("nearby", "gyms.nearby") or "k" not in payload:
        raise ValueError("invalid page_token")
    k = payload["k"]
    if not (isinstance(k, list) and len(k) == 2):
        raise ValueError("invalid page_token")
    return float(k[0]), int(k[1])


def _iso(dt: datetime | None) -> str | None:
    if not dt or (hasattr(dt, "year") and dt.year < 1970):
        return None
    return dt.isoformat()


async def search_nearby(
    session: AsyncSession,
    *,
    lat: float,
    lng: float,
    radius_km: float,
    page: int,
    page_size: int | None,
    page_token: str | None,
) -> GymNearbyResponse:
    logger = structlog.get_logger(__name__)
    """Nearby gyms using Haversine distance with offset pagination."""

    per_page = int(page_size or 20)
    if per_page <= 0:
        per_page = 20
    per_page = max(1, min(per_page, 100))

    current_page = int(page or 1)
    if current_page <= 0:
        current_page = 1
    offset = (current_page - 1) * per_page
    use_keyset = bool(page_token)

    # Precompute radians of input
    lat0 = float(lat)
    lng0 = float(lng)

    lat_rad = func.radians(Gym.latitude)
    lng_rad = func.radians(Gym.longitude)
    lat0_rad = func.radians(literal(lat0))
    lng0_rad = func.radians(literal(lng0))

    dlat = lat_rad - lat0_rad
    dlng = lng_rad - lng0_rad

    # Haversine formula
    a = func.pow(func.sin(dlat / 2.0), 2) + func.cos(lat0_rad) * func.cos(lat_rad) * func.pow(
        func.sin(dlng / 2.0), 2
    )
    c = 2.0 * func.asin(func.sqrt(func.least(1.0, a)))
    distance_km_expr = 6371.0 * c
    # Use numeric(18,6) for stable ordering and token
    dist_num = cast(distance_km_expr, Numeric(18, 6))

    base_stmt = (
        select(Gym, dist_num.label("distance_km"))
        .where(and_(Gym.latitude.is_not(None), Gym.longitude.is_not(None)))
        .where(dist_num <= float(radius_km))
    )

    total = (await session.scalar(select(func.count()).select_from(base_stmt.subquery()))) or 0
    if total == 0:
        return GymNearbyResponse(
            items=[],
            total=0,
            page=current_page,
            page_size=per_page,
            has_more=False,
            has_prev=current_page > 1,
            page_token=None,
        )

    stmt = base_stmt

    if use_keyset and page_token:
        lk_dist, lk_id = _validate_and_decode_page_token(page_token)
        stmt = stmt.where(tuple_(dist_num, Gym.id) > tuple_(literal(lk_dist), literal(int(lk_id))))

    stmt = stmt.order_by(dist_num.asc(), Gym.id.asc())
    if use_keyset:
        stmt = stmt.limit(per_page + 1)
    else:
        stmt = stmt.offset(offset).limit(per_page)

    rows = (await session.execute(stmt)).all()
    page_rows = rows[:per_page] if use_keyset else rows

    items: list[GymNearbyItem] = []
    for g, dist in page_rows:
        lat_val = getattr(g, "latitude", None)
        lng_val = getattr(g, "longitude", None)
        items.append(
            GymNearbyItem(
                id=int(getattr(g, "id", 0)),
                slug=str(getattr(g, "slug", "")),
                name=str(getattr(g, "name", "")),
                pref=str(getattr(g, "pref", "")),
                city=str(getattr(g, "city", "")),
                latitude=float(lat_val or 0.0),
                longitude=float(lng_val or 0.0),
                distance_km=float(dist or 0.0),
                last_verified_at=_iso(getattr(g, "last_verified_at_cached", None)),
            )
        )

    next_token = None
    if use_keyset:
        has_more = len(rows) > per_page
        has_prev = current_page > 1 or bool(page_token)
        if has_more:
            last_row = rows[per_page - 1]
            g_last, dist_last = last_row
            next_token = _encode_page_token_for_nearby(
                float(dist_last or 0.0), int(getattr(g_last, "id", 0))
            )
    else:
        has_more = (offset + len(items)) < total
        has_prev = offset > 0

    logger.info(
        "gyms_nearby",
        lat=float(lat),
        lng=float(lng),
        radius_km=float(radius_km),
        returned=len(items),
        page=current_page,
        page_size=per_page,
    )
    return GymNearbyResponse(
        items=items,
        total=total,
        page=current_page,
        page_size=per_page,
        has_more=has_more,
        has_prev=has_prev,
        page_token=next_token,
    )
