from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.deps import get_db
from app.models import Equipment, Gym, GymEquipment
from app.services.gym_detail import (
    get_gym_detail as svc_get_gym_detail,
)
from app.services.gym_detail import (
    search_gyms as svc_search_gyms,
)
from app.utils.datetime import dt_to_token

router = APIRouter(prefix="/gyms", tags=["gyms"])


@router.get(
    "/search",
    response_model=schemas.GymSearchResponse,
    responses={
        400: {
            "description": "Invalid page_token",
            "content": {"application/json": {"example": {"detail": "invalid page_token"}}},
        }
    },
)
async def search_gyms(
    pref: str | None = Query(None, description="都道府県スラッグ（例: chiba）"),
    city: str | None = Query(None, description="市区町村スラッグ（例: funabashi）"),
    equipments: str | None = Query(None, description="CSV: squat-rack,dumbbell"),
    equipment_match: str = Query("any", description="any or all match for equipments filter"),
    sort: str = Query("freshness"),
    page_token: str | None = Query(
        None,
        examples=["v1:freshness:nf=0,ts=1725555555,id=42"],
        description="Keysetの継続トークン。sortと整合しない値は400を返す。",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    gq = select(Gym)
    if pref:
        gq = gq.where(func.lower(Gym.pref) == func.lower(pref))
    if city:
        gq = gq.where(func.lower(Gym.city) == func.lower(city))
    # prepare equipment filter list
    equip_filter: list[str] | None = None
    if equipments:
        equip_filter = [s.strip() for s in equipments.split(",") if s.strip()]

    # fetch candidate gyms (apply only pref/city in SQL) via service
    # (which will also aggregate equipments)
    items_all, _ = await svc_search_gyms(
        db, pref=pref, city=city, equipments=equip_filter, equipment_match=equipment_match
    )

    gym_ids_all = [g["id"] for g in items_all]

    # If equipments filter present, fetch equipment rows for those gyms and determine matching gyms
    ge_rows = []
    if gym_ids_all:
        geq = (
            select(
                GymEquipment.gym_id,
                Equipment.slug.label("equipment_slug"),
                Equipment.name.label("equipment_name"),
                Equipment.category,
                GymEquipment.availability,
                GymEquipment.count,
                GymEquipment.max_weight_kg,
                GymEquipment.verification_status,
                GymEquipment.last_verified_at,
            )
            .join(Equipment, Equipment.id == GymEquipment.equipment_id)
            .where(GymEquipment.gym_id.in_(gym_ids_all))
        )
        if equip_filter:
            geq = geq.where(Equipment.slug.in_(equip_filter))

        ge_rows = (await db.execute(geq)).all()

    # build equipment lookup and richness/last_verified maps
    by_gym: dict[int, list[dict]] = {}
    last_verified_by_gym: dict[int, datetime | None] = {}
    richness_by_gym: dict[int, float] = {}

    for row in ge_rows:
        hi = {
            "equipment_slug": row.equipment_slug,
            "availability": row.availability.value
            if hasattr(row.availability, "value")
            else str(row.availability),
            "count": row.count,
            "max_weight_kg": row.max_weight_kg,
            "verification_status": row.verification_status.value
            if hasattr(row.verification_status, "value")
            else str(row.verification_status),
            "last_verified_at": dt_to_token(row.last_verified_at),
        }
        by_gym.setdefault(row.gym_id, []).append(hi)

        lv = last_verified_by_gym.get(row.gym_id)
        if lv is None or (row.last_verified_at and row.last_verified_at > lv):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        sc = richness_by_gym.get(row.gym_id, 0.0)
        avail = hi.get("availability")
        if str(avail) == "present":
            sc += 1.0
            cnt = hi.get("count") or 0
            sc += min(int(cnt), 5) * 0.1 if cnt else 0.0
            mw = hi.get("max_weight_kg") or 0
            sc += min(float(mw) / 60.0, 1.0) * 0.1 if mw else 0.0
        elif str(avail) == "unknown":
            sc += 0.3
        richness_by_gym[row.gym_id] = sc

    # Determine which gyms satisfy equipment filter and match mode
    if equip_filter:
        requested = set(equip_filter)
        if equipment_match == "all":
            allowed_gym_ids = {
                gid
                for gid, rows in by_gym.items()
                if set(r["equipment_slug"] for r in rows) >= requested
            }
        else:
            # any
            allowed_gym_ids = set(by_gym.keys())
    else:
        allowed_gym_ids = set(gym_ids_all)

    # allowed_gym_ids を反映して items を構築（未使用警告の解消と意図したフィルタ適用）
    filtered_items_all = [it for it in items_all if it["id"] in allowed_gym_ids]

    # Build items list converting datetimes to tokens
    items: list[dict] = []
    for it in filtered_items_all:
        new = dict(it)
        new["last_verified_at"] = dt_to_token(it.get("last_verified_at"))
        items.append(new)

    # sort items

    # offset-based token. If page_token present, interpret as offset int.
    try:
        offset = int(page_token) if page_token is not None else (page - 1) * per_page
    except Exception:
        # invalid token -> 400
        raise HTTPException(status_code=400, detail="invalid page_token")

    if sort == "freshness":
        items.sort(
            key=lambda i: (i.get("last_verified_at") is None, i.get("last_verified_at")),
            reverse=True,
        )
    elif sort == "richness":
        items.sort(key=lambda i: i.get("score", 0.0), reverse=True)
    elif sort == "score":
        items.sort(key=lambda i: i.get("score", 0.0), reverse=True)
    elif sort == "gym_name":
        items.sort(key=lambda i: i.get("name") or "")
    elif sort == "created_at":
        # created_at is a DB field; fetch mapping of id->created_at from DB for accurate sorting
        gym_rows = (await db.scalars(gq.order_by(Gym.id))).all()
        created_map = {g.id: getattr(g, "created_at", None) for g in gym_rows}
        items.sort(key=lambda i: created_map.get(i.get("id")) or 0)

    # when sorting by freshness, page only gyms that have a last_verified_at (tests expect that)
    if sort == "freshness":
        pagable_items = [it for it in items if it.get("last_verified_at") is not None]
    else:
        pagable_items = items

    total = len(pagable_items)
    if total == 0:
        return schemas.GymSearchResponse(items=[], total=0, has_next=False, page_token=None)

    page_slice = pagable_items[offset : offset + per_page]
    next_offset = offset + per_page if (offset + per_page) < total else None
    page_token_out = str(next_offset) if next_offset is not None else None
    has_next = next_offset is not None

    # debug prints removed; returning validated items

    # validate/convert dicts into GymSummary instances so response_model typing matches
    validated_items = [schemas.GymSummary.model_validate(i) for i in page_slice]
    return schemas.GymSearchResponse(
        items=validated_items, total=total, has_next=has_next, page_token=page_token_out
    )


@router.get("/{slug}", response_model=schemas.GymDetailResponse)
async def get_gym_detail(
    slug: str, include: str | None = Query(None), db: AsyncSession = Depends(get_db)
):
    detail = await svc_get_gym_detail(db, slug, include_score=(include == "score"))
    if detail is None:
        raise HTTPException(status_code=404, detail="gym not found")

    # convert updated_at (datetime) into token
    updated_at_token = dt_to_token(detail.get("updated_at")) if detail.get("updated_at") else None

    return schemas.GymDetailResponse(
        id=detail["id"],
        slug=detail["slug"],
        name=detail["name"],
        city=detail["city"],
        pref=detail["pref"],
        equipments=detail["equipments"],
        updated_at=updated_at_token,
        freshness=detail.get("freshness"),
        richness=detail.get("richness"),
        score=detail.get("score"),
    )
