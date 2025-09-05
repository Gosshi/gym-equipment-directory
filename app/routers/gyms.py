from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.deps import get_db
from app import schemas
from app.models import (
    Gym, Equipment, GymEquipment, Source,
    Availability, VerificationStatus
)

router = APIRouter(prefix="/gyms", tags=["gyms"])

@router.get("/search", response_model=schemas.SearchResponse)
async def search_gyms(
    pref: Optional[str] = Query(None, description="都道府県スラッグ（例: chiba）"),
    city: Optional[str] = Query(None, description="市区町村スラッグ（例: funabashi）"),
    equipments: Optional[str] = Query(None, description="CSV: squat-rack,dumbbell"),
    sort: str = Query("freshness", pattern="^(richness|freshness)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    gq = select(Gym)
    if pref:
        gq = gq.where(func.lower(Gym.prefecture) == func.lower(pref))
    if city:
        gq = gq.where(func.lower(Gym.city) == func.lower(city))

    total = await db.scalar(select(func.count()).select_from(gq.subquery())) or 0
    if total == 0:
        return schemas.SearchResponse(items=[], page=page, per_page=per_page, total=0)

    gq = gq.order_by(Gym.id).offset((page - 1) * per_page).limit(per_page)
    gyms: List[Gym] = (await db.scalars(gq)).all()

    equip_filter: Optional[List[str]] = None
    if equipments:
        equip_filter = [s.strip() for s in equipments.split(",") if s.strip()]

    gym_ids = [g.id for g in gyms]

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
            GymEquipment.last_verified_at
        )
        .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        .where(GymEquipment.gym_id.in_(gym_ids))
    )
    if equip_filter:
        geq = geq.where(Equipment.slug.in_(equip_filter))

    ge_rows = (await db.execute(geq)).all()

    by_gym: Dict[int, List[schemas.EquipmentHighlight]] = {}
    last_verified_by_gym: Dict[int, Optional[str]] = {}
    richness_by_gym: Dict[int, float] = {}

    for row in ge_rows:
        hi = schemas.EquipmentHighlight(
            equipment_slug=row.equipment_slug,
            availability=row.availability.value if hasattr(row.availability, "value") else str(row.availability),
            count=row.count,
            max_weight_kg=row.max_weight_kg,
            verification_status=row.verification_status.value if hasattr(row.verification_status, "value") else str(row.verification_status),
            last_verified_at=row.last_verified_at
        )
        by_gym.setdefault(row.gym_id, []).append(hi)

        lv = last_verified_by_gym.get(row.gym_id)
        if lv is None or (row.last_verified_at and row.last_verified_at > lv):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        sc = richness_by_gym.get(row.gym_id, 0.0)
        if str(hi.availability) == "present":
            sc += 1.0
            if hi.count:
                sc += min(hi.count, 5) * 0.1
            if hi.max_weight_kg:
                sc += min(hi.max_weight_kg / 60.0, 1.0) * 0.1
        elif str(hi.availability) == "unknown":
            sc += 0.3
        richness_by_gym[row.gym_id] = sc

    items: List[schemas.SearchItem] = []
    for g in gyms:
        item = schemas.SearchItem(
            gym=schemas.GymBasic.model_validate(g),
            highlights=by_gym.get(g.id, []),
            last_verified_at=last_verified_by_gym.get(g.id),
            score=richness_by_gym.get(g.id, 0.0),
        )
        items.append(item)

    if sort == "freshness":
        items.sort(key=lambda i: (i.last_verified_at is None, i.last_verified_at), reverse=True)
    elif sort == "richness":
        items.sort(key=lambda i: i.score, reverse=True)

    return schemas.SearchResponse(items=items, page=page, per_page=per_page, total=total)


@router.get("/{slug}", response_model=schemas.GymDetailResponse)
async def get_gym_detail(slug: str, db: AsyncSession = Depends(get_db)):
    gym = await db.scalar(select(Gym).where(Gym.slug == slug))
    if not gym:
        raise HTTPException(status_code=404, detail="gym not found")

    geq = (
        select(
            Equipment.slug.label("equipment_slug"),
            Equipment.name.label("equipment_name"),
            Equipment.category,
            GymEquipment.availability,
            GymEquipment.count,
            GymEquipment.max_weight_kg,
            GymEquipment.verification_status,
            GymEquipment.last_verified_at
        )
        .join(Equipment, Equipment.id == GymEquipment.equipment_id)
        .where(GymEquipment.gym_id == gym.id)
        .order_by(Equipment.category, Equipment.name)
    )
    ge_rows = (await db.execute(geq)).all()

    equipments = [
        schemas.EquipmentRow(
            equipment_slug=r.equipment_slug,
            equipment_name=r.equipment_name,
            category=r.category,
            availability=r.availability.value if hasattr(r.availability, "value") else str(r.availability),
            count=r.count,
            max_weight_kg=r.max_weight_kg,
            verification_status=r.verification_status.value if hasattr(r.verification_status, "value") else str(r.verification_status),
            last_verified_at=r.last_verified_at,
        )
        for r in ge_rows
    ]

    sources: List[schemas.SourceRow] = []
    updated_at = None
    for r in ge_rows:
        if r.last_verified_at and (updated_at is None or r.last_verified_at > updated_at):
            updated_at = r.last_verified_at

    return schemas.GymDetailResponse(
        gym=schemas.GymBasic.model_validate(gym),
        equipments=equipments,
        sources=sources,
        updated_at=updated_at
    )
