from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.deps import get_db
from app.models import Equipment, Gym, GymEquipment
from app.services.gym_search import search_gyms as svc_search_gyms_service

router = APIRouter(prefix="/gyms", tags=["gyms"])


def _as_utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # UTCにそろえてtzinfoを剥がす（DBはnaive列）
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _dt_from_token(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # "Z" を含む場合のフォールバック
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return _as_utc_naive(dt)


def _dt_to_token(dt: datetime | None) -> str | None:
    dt = _as_utc_naive(dt)
    return dt.isoformat(timespec="seconds") if dt else None


@router.get(
    "/search",
    response_model=schemas.SearchResponse,
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
    sort: str = Query("freshness", pattern="^(richness|freshness)$"),
    page_token: str | None = Query(
        None,
        example="v1:freshness:nf=0,ts=1725555555,id=42",
        description="Keysetの継続トークン。sortと整合しない値は400を返す。",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    # CSV -> list[str]
    equip_list: list[str] | None = None
    if equipments:
        equip_list = [s.strip() for s in equipments.split(",") if s.strip()]

    # service に委譲（routerは入出力整形のみ）
    try:
        result = await svc_search_gyms_service(
            db,
            pref=pref,
            city=city,
            equipments=equip_list,
            equipment_match="any",  # 既定は any
            sort=sort,
            page_token=page_token,
            page=page,
            per_page=per_page,
        )
    except ValueError:
        # 無効な page_token など
        raise HTTPException(status_code=400, detail="invalid page_token")

    # service -> schemas へ詰め替え
    items: list[schemas.SearchItem] = []
    for it in result["items"]:
        items.append(
            schemas.SearchItem(
                gym=schemas.GymBasic.model_validate(
                    {
                        "id": it.get("id"),
                        "slug": it.get("slug"),
                        "name": it.get("name"),
                        "pref": it.get("pref"),
                        "city": it.get("city"),
                    }
                ),
                highlights=[],  # 必要なら後段で拡張
                last_verified_at=it.get("last_verified_at"),
                score=float(it.get("score", 0.0)),
            )
        )

    return schemas.SearchResponse(items=items, page=page, per_page=per_page, total=result["total"])


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
            GymEquipment.last_verified_at,
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
            availability=(
                r.availability.value if hasattr(r.availability, "value") else str(r.availability)
            ),
            count=r.count,
            max_weight_kg=r.max_weight_kg,
            verification_status=(
                r.verification_status.value
                if hasattr(r.verification_status, "value")
                else str(r.verification_status)
            ),
            last_verified_at=r.last_verified_at,
        )
        for r in ge_rows
    ]

    sources: list[schemas.SourceRow] = []
    updated_at = None
    for r in ge_rows:
        if r.last_verified_at and (updated_at is None or r.last_verified_at > updated_at):
            updated_at = r.last_verified_at

    return schemas.GymDetailResponse(
        gym=schemas.GymBasic.model_validate(gym),
        equipments=equipments,
        sources=sources,
        updated_at=updated_at,
    )